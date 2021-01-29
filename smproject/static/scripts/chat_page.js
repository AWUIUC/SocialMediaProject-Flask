document.addEventListener('DOMContentLoaded', () => {
  // Make pressing 'enter' key same as clicking send message button
  let msg = document.querySelector('#user_message');
  msg.addEventListener('keyup', event => {
    event.preventDefault();
    if (event.keyCode === 13) {
      document.querySelector('#send_message').click();
    }
  })
})
