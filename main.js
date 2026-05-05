document.getElementById('drawBtn').addEventListener('click', drawLotto);

function getBallClass(num) {
  if (num <= 10) return 'yellow';
  if (num <= 20) return 'blue';
  if (num <= 30) return 'red';
  if (num <= 40) return 'gray';
  return 'green';
}

function drawLotto() {
  const btn = document.getElementById('drawBtn');
  btn.disabled = true;

  // 1~45 중 6개 비복원 추출
  const pool = Array.from({ length: 45 }, (_, i) => i + 1);
  const picked = [];
  for (let i = 0; i < 6; i++) {
    const idx = Math.floor(Math.random() * pool.length);
    picked.push(pool.splice(idx, 1)[0]);
  }
  picked.sort((a, b) => a - b);

  // 볼 하나씩 순서대로 표시
  const balls = document.querySelectorAll('#ballsContainer .ball');
  balls.forEach(b => {
    b.className = 'ball empty';
    b.textContent = '';
  });

  picked.forEach((num, i) => {
    setTimeout(() => {
      const ball = balls[i];
      ball.className = `ball ${getBallClass(num)} pop`;
      ball.textContent = num;
      if (i === 5) {
        addHistory(picked);
        btn.disabled = false;
      }
    }, i * 300);
  });
}

function addHistory(numbers) {
  const list = document.getElementById('historyList');
  const li = document.createElement('li');

  numbers.forEach(num => {
    const span = document.createElement('span');
    span.className = `mini-ball ${getBallClass(num)}`;
    span.textContent = num;
    li.appendChild(span);
  });

  list.insertBefore(li, list.firstChild);

  // 최근 10회까지만 보관
  while (list.children.length > 10) {
    list.removeChild(list.lastChild);
  }
}
