source /root/.bashrc
cd /root/Legal-NLP-EkStep.github.io
git pull
rm -rf /root/Legal-NLP-EkStep.github.io/Competitions/Rhetorical-Role/leaderboard/out.json
python /root/Legal-NLP-EkStep.github.io/Competitions/Rhetorical-Role/leaderboard/leaderboard_utils.py
sudo shutdown