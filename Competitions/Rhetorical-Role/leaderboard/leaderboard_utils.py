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
        print(stdout.decode('utf-8'),'\n\n', stderr.decode('utf-8'))
        return stdout.decode('utf-8'), stderr.decode('utf-8')

    def check_and_load_secrets(self, secrets_json_path):
        secrets = json.load(open(secrets_json_path)) if os.path.exists(secrets_json_path) else sys.exit(
            'Error: Secrets json not found')
        self.competition_yml_path = secrets['competition_yml_path'] if os.path.exists(
            secrets['competition_yml_path']) else sys.exit(
            'Error: Competition config yml not found')
        self.master_leaderboard_json_path = os.path.abspath(secrets['master_leaderboard_json_path'])
        self.final_leaderboard_json_path = os.path.abspath(secrets['final_leaderboard_json_path'])
        self.codalab_user_name = secrets['codalab_user_name']
        self.codalab_user_password = secrets['codalab_user_password']
        os.environ['CODALAB_USERNAME'] = self.codalab_user_name
        os.environ['CODALAB_PASSWORD'] = self.codalab_user_password
        self.bucket_path = secrets['bucket_path']
        self.push_to_bucket = secrets['push_to_gcp_bucket']
        self.push_to_git = secrets['push_to_git']

    def load_master_leaderboard_and_save_it(self):
        leaderboard = json.load(open(self.master_leaderboard_json_path))
        leaderboard['leaderboard'] = [i for i in leaderboard['leaderboard'] if
                                      type(i['scores']['Weighted-F1']) == float]
        for each_entry in leaderboard['leaderboard']:
            description = json.loads(each_entry['submission']['description'])
            for key in description.keys():
                if description[key].upper() == 'NONE':
                    description[key] = 'Anonymous'
                each_entry['submission'][key] = description[key]
        leaderboard['leaderboard'] = sorted(leaderboard['leaderboard'], key=lambda x: x['scores']['Weighted-F1'],
                                            reverse=True)
        with open(self.final_leaderboard_json_path, 'w') as f:
            json.dump(leaderboard, f, indent=4)

    def upload_master_leaderboard_file_to_bucket(self):
        if self.push_to_bucket:
            assert 'gs://' in self.bucket_path, "Wrong bucket path"
            command = f'gsutil -m cp -r {self.master_leaderboard_json_path} {self.bucket_path}'
            _, _ = self.execute_terminal_command_and_return_stdout_stderr(command)
            command = f'gsutil -m cp -r {self.final_leaderboard_json_path} {self.bucket_path}'
            _, _ = self.execute_terminal_command_and_return_stdout_stderr(command)
            print("***************Pushed to bucket successfully***************")

    def push_final_leaderboard_json_to_git(self):
        if self.push_to_git:
            now = datetime.now()
            dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
            command = f'git add {self.final_leaderboard_json_path.split("/")[-1]}'
            output, error = self.execute_terminal_command_and_return_stdout_stderr(command)
            command = f'git commit -m "Update: {dt_string}"'
            output, error = self.execute_terminal_command_and_return_stdout_stderr(command)
            command = f'git push'
            output, error = self.execute_terminal_command_and_return_stdout_stderr(command)

    def schedule_evaluation_jobs_and_update_leaderboard(self):
        command = f'cl-competitiond {self.competition_yml_path} {self.master_leaderboard_json_path}'
        output, error = self.execute_terminal_command_and_return_stdout_stderr(command)
        self.load_master_leaderboard_and_save_it()

    def update_leaderboard_only(self):
        command = f'cl-competitiond -l {self.competition_yml_path} {self.master_leaderboard_json_path}'
        output, error = self.execute_terminal_command_and_return_stdout_stderr(command)
        self.load_master_leaderboard_and_save_it()

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
    obj = LeaderboardUtils(os.path.join(os.path.split(os.path.abspath(__file__))[0],"secrets.json"))
    obj.schedule_evaluation_jobs_and_update_leaderboard()
    for i in range(150):  # here 150 would mean that this loop will execute every 5 minutes for next 12 hrs and stop if all jobs are completed
        obj.clean_up_of_completed_job_resources()
        if obj.pending_jobs_count == 0:
            break
        sleep(300)
    obj.update_leaderboard_only()
    obj.upload_master_leaderboard_file_to_bucket()
    # For Git commits: Complete these steps.
    # 1. Run: git config --global credential.helper store #This will store your credentials in git when you enter next time
    # 2. Run: git push #So that your credentials get stored
    # 3. Run: git config --global user.email "you@example.com"
    # 4. Run: git config --global user.name "Your Name"
    # Only after these steps you will see updates in git
    obj.push_final_leaderboard_json_to_git()
