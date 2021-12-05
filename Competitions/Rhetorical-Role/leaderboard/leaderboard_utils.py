import json
import os
from datetime import datetime
import subprocess
import sys
from time import sleep


class LeaderboardUtils:
    def __init__(self, secrets_json_path):
        self.check_and_load_secrets(secrets_json_path)

    @staticmethod
    def execute_terminal_command_and_return_stdout_stderr(command):
        stdout, stderr = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE).communicate()
        return stdout.decode('utf-8'), stderr.decode('utf-8')

    def check_and_load_secrets(self, secrets_json_path):
        secrets = json.load(open(secrets_json_path)) if os.path.exists(secrets_json_path) else sys.exit(
            'Error: Secrets json not found')
        self.competition_yml_path = secrets['competition_yml_path'] if os.path.exists(
            secrets['competition_yml_path']) else sys.exit(
            'Error: Competition config yml not found')
        self.master_leaderboard_json_path = os.path.abspath(secrets['master_leaderboard_json_path'])
        self.final_leaderboard_json_path = os.path.abspath(secrets['final_leaderboard_json_path'])
        os.makedirs(self.master_leaderboard_json_path, exist_ok=True)
        self.bucket_path = secrets['bucket_path']
        self.push_to_bucket = secrets['push_to_gcp_bucket']
        self.push_to_git = secrets['push_to_git']
        self.gitusername = secrets['gitusername']
        self.gittoken = secrets['gittoken']

    def load_master_leaderboard_and_save_it(self):
        leaderboard = json.load(open(self.master_leaderboard_json_path))
        leaderboard['leaderboard'] = [i for i in leaderboard['leaderboard'] if
                                      type(i['scores']['Weighted-F1']) == float]
        for each_entry in leaderboard['leaderboard']:
            description = json.loads(each_entry['submission']['description'])
            for key in description.keys():
                if description[key].upper() == 'NONE':
                    description[key] = 'Anonymous'
                each_entry['submission']['description'][key] = description[key]
        leaderboard['leaderboard'] = sorted(leaderboard['leaderboard'], key=lambda x: x['scores']['Weighted-F1'],
                                            reverse=True)
        with open(self.final_leaderboard_json_path, 'w') as f:
            json.dump(leaderboard, f, indent=4)

    def upload_master_leaderboard_file_to_bucket(self):
        if self.push_to_bucket:
            assert 'gs://' in self.bucket_path, "Wrong bucket path"
            command = f'gsutil -m cp -r {self.master_leaderboard_json_path} {self.bucket_path}'
            _, _ = self.execute_terminal_command_and_return_stdout_stderr(command)

    def push_final_leaderboard_json_to_git(self):
        if self.push_to_git:
            now = datetime.now()
            dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
            command = 'git pull --rebase'
            _, _ = self.execute_terminal_command_and_return_stdout_stderr(command)
            command = f'git commit -m "Update: {dt_string}"'
            _, _ = self.execute_terminal_command_and_return_stdout_stderr(command)
            command = f'{self.gitusername} | {self.gittoken} | git push'
            _, _ = self.execute_terminal_command_and_return_stdout_stderr(command)

    def schedule_evaluation_jobs_and_update_leaderboard(self):
        command = f'cl-competitiond {self.competition_yml_path} {self.master_leaderboard_json_path}'
        output, error = self.execute_terminal_command_and_return_stdout_stderr(command)
        if error:
            print(error)
            sys.exit("Error: Command not executed properly check above to debug")
        else:
            self.load_master_leaderboard_and_save_it()
            self.upload_master_leaderboard_file_to_bucket()
            self.push_final_leaderboard_json_to_git()

    def update_leaderboard_only(self):
        command = f'cl-competitiond -l {self.competition_yml_path} {self.master_leaderboard_json_path}'
        output, error = self.execute_terminal_command_and_return_stdout_stderr(command)
        if error:
            print(error)
            sys.exit("Error: Command not executed properly check above to debug")
        else:
            self.load_master_leaderboard_and_save_it()
            self.upload_master_leaderboard_file_to_bucket()
            self.push_final_leaderboard_json_to_git()

    def clean_up_of_completed_job_resources(self):
        if not os.path.exists(self.master_leaderboard_json_path):
            sys.exit('LeaderBoard not yet created')
        leaderboard = json.load(open(self.master_leaderboard_json_path))
        self.pending_jobs_count = 0
        if leaderboard['leaderboard']:
            entries = leaderboard['leaderboard']
            for each_entry in entries:
                final_id_with_result = each_entry['bundle']['id']
                command = f'cl info {final_id_with_result}'
                output, error = self.execute_terminal_command_and_return_stdout_stderr(command)
                parsed_output_with_status = [i for i in output.split('\n') if 'run_status' in i]
                status = True if parsed_output_with_status[0].split(":")[-1].strip() == 'Finished' else False
                entry_with_parent_id = [val for val in each_entry['bundle']['dependencies'] if
                                        val['child_path'] == 'predictions.json']
                if entry_with_parent_id:
                    parent_id = entry_with_parent_id[0]['parent_uuid']
                    if status:
                        command = f'cl rm -d {parent_id} --force'
                        output, error = self.execute_terminal_command_and_return_stdout_stderr(command)
                    else:
                        self.pending_jobs_count += 1
                else:
                    pass
        else:
            sys.exit('Error: No jobs found to cleanup')


if __name__ == "__main__":
    obj = LeaderboardUtils("./secrets.json")
    obj.schedule_evaluation_jobs_and_update_leaderboard()
    for i in range(150): # here 150 would mean that this loop will execute every 5 minutes for next 12 hrs and stop if all jobs are completed
        sleep(300)
        obj.clean_up_of_completed_job_resources()
        if obj.pending_jobs_count == 0:
            break
    obj.update_leaderboard_only()