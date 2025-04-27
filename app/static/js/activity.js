let keyCount = 0;
let mouseCount = 0;

document.addEventListener('keydown', () => {
    keyCount++;
});

document.addEventListener('mousemove', () => {
    mouseCount++;
});

setInterval(() => {
    fetch('/api/activity', {
        method: 'POST',
        body: JSON.stringify({ keyCount, mouseCount }),
        headers: { 'Content-Type': 'application/json' },
    }).then(response => response.json())
      .then(data => console.log('Activity Score:', data.activity_score));
    
    keyCount = 0;
    mouseCount = 0;
}, 60000);