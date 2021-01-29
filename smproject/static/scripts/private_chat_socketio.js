$(document).ready(function() {
    var socket = io.connect('http://' + document.domain + ':' + location.port);

    let recipient = user_email;

    socket.on('connect', () => {
      console.log('sid being updated')
      socket.emit('add_or_update_sid')
    });


    // New recipient selection
    document.querySelectorAll('.select_recipient_button').forEach(p => {  //we use .select-room instead of #select-room since select-room is a class instead of id
      p.onclick = () => {
        //Update recipient
        recipient = p.innerHTML;
        console.log("Recipient updated: " + p.innerHTML);

        //Clear message section
        document.getElementById('messages_list').innerHTML = '';

        //Get history of private messages from server
        socket.emit('get_message_history', {'recipient_user_email': recipient});
      }
    });

    //Sending private messages
    $('#send_private_message').on('click', function() {
        var message_to_send = $('#private_message').val();
        socket.emit('private_message', {'recipient_email' : recipient, 'message' : message_to_send});
    });

    //Receiving and loading private messages
    socket.on('receive_new_private_message', function(data) {
      if (user_email == data['sender']) {
        if (recipient == data['recipient']) { //if recipient (person you are talking to) is the recipient AND you are the sender then display message
          //console.log(data);
          //console.log(data['testkey1'])
          $("#messages_list").append('<li>' + "Sender: " + data['sender'] + '</li>');
          $("#messages_list").append('<li>' + "To: " + data['recipient'] + '</li>');
          $("#messages_list").append('<li>' + "Message: " + data['message_data'] + '</li>');
          $("#messages_list").append('<li>' +  '<br>' + '</li>');
        }
      } else if (user_email == data['recipient']) {
        if (recipient == data['sender']) { //if you are the recipient of a message AND the chat box you have opened is with the sender then display msg
          $("#messages_list").append('<li>' + "Sender: " + data['sender'] + '</li>');
          $("#messages_list").append('<li>' + "To: " + data['recipient'] + '</li>');
          $("#messages_list").append('<li>' + "Message: " + data['message_data'] + '</li>');
          $("#messages_list").append('<li>' +  '<br>' + '</li>');
        }
      }

    });

});
