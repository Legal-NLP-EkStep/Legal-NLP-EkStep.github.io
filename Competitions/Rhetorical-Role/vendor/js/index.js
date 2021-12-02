const toDate = (epoch) =>{
  return new Date(epoch).toDateString().substring(4);
}

const createRankTd = (rank, lastUpdateDate) =>{
  const td1 = document.createElement('td');
  td1.scope = 'row';
  td1.className = 'align-middle text-center'
  td1.innerText = rank;
  
  const br1 = document.createElement('br');
  const span1 = document.createElement('span');

  span1.innerText = lastUpdateDate;
  span1.className = 'badge badge-secondary'

  td1.appendChild(br1);
  td1.appendChild(span1);
  return td1;
}

const createModelTd = (model, company) =>{
  const td2 = document.createElement('td');
  td2.className = 'align-middle text-center'
  td2.innerText = model;

  const br2 = document.createElement('br');
  const brSecond2 = document.createElement('br');
  td2.appendChild(br2);

  const span2 = document.createElement('span');
  span2.className = 'affiliation'
  span2.innerText = company;
  
  td2.appendChild(span2);
  td2.appendChild(brSecond2);
  return td2
}

const createCodeTd = (hasCode, link) =>{
  const td3 = document.createElement('td');
  td3.className = 'align-middle text-center'

  const div3 = document.createElement('div');
  div3.className = 'crossed'

  const i3 = document.createElement('i');
  i3.className = 'far fa-file text-danger'

  if(hasCode){
    const a3 = document.createElement('a')
    a3.href = link;
    i3.className = 'far fa-file-alt'
    a3.appendChild(i3);
    td3.appendChild(a3)
    return td3;
  }

  div3.appendChild(i3);
  td3.appendChild(div3)
  return td3;
}

const createWeightedF1Td = (weightedF1) =>{
  const td4 = document.createElement('td');
  td4.className = 'align-middle text-center'
  td4.innerText = weightedF1;
  return td4;
}

const codeUrl = (host, bundleId) => {
  return host + '/bundles/' + bundleId + '/'
}

const attachLeaderboard = (leaderboard, rank, host) => {
  const leaderboardBody = document.getElementById('leaderboard')
  const tr = document.createElement('tr');

  const td1 = createRankTd(rank, toDate(leaderboard.bundle.metadata.last_updated * 1000));
  const td2 = createModelTd(leaderboard.submission.model_name, leaderboard.submission.affiliation);
  const td3 = createCodeTd(leaderboard.submission.public, leaderboard.submission.code_link);
  const td4 = createWeightedF1Td((leaderboard.scores["Weighted-F1"]*100).toFixed(2));

  tr.appendChild(td1);
  tr.appendChild(td2);
  tr.appendChild(td3);
  tr.appendChild(td4);

  leaderboardBody.appendChild(tr)
}

const fetchData = async() => {
  const response = await fetch('https://raw.githubusercontent.com/Legal-NLP-EkStep/Legal-NLP-EkStep.github.io/main/out.json');
  const responseAsJson = (await response.json());
  const leaderboardScores = responseAsJson.leaderboard;
  const host = responseAsJson.config.host
  
  leaderboardScores.forEach((score, index) => {
    attachLeaderboard(score, index + 1, host);
  });
}

window.onload = fetchData;