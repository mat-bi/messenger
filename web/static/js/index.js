$('.chat[data-chat=person2]').addClass('active-chat');
$('.person[data-chat=person2]').addClass('active');

$('.left .person').mousedown(function(){
    if ($(this).hasClass('.active')) {
        return false;
    } else {
        var findChat = $(this).attr('data-chat');
        var personName = $(this).find('.name').text();
        $('.right .top .name').html(personName);
        $('.chat').removeClass('active-chat');
        $('.left .person').removeClass('active');
        $(this).addClass('active');
        $('.chat[data-chat = '+findChat+']').addClass('active-chat');
    }
});

// function WebSocketTest() {
//     if ("WebSocket" in window) {
//         alert("WebSocket is supported by your Browser!");
//         // Let us open a web socket
//         var ws = new WebSocket("ws://127.0.0.1:3000/websocket");
//
//         var register = {
//             "type": 1,
//             "login": "login3",
//             "password": "password3"
//         };
//
//         var message = {
//             "type" : "2",
//             "message" : {
//                 "content" : "hue"
//             }
//         };
//
//         ws.onopen = function () {
//             // Web Socket is connected, send data using send()
//             ws.send(JSON.stringify({"type": 1, "login": "login3", "password": "password3"}));
//             // var t = document.getElementById("text").value;
//             // ws.send(JSON.stringify({"type":2, "message": {"content": t}}));
//             alert("Message is sent...");
//         };
//
//         ws.onmessage = function (evt) {
//             var received_msg = evt.data;
//             console.log(received_msg);
//             alert("Message is received...");
//         };
//
//         ws.onclose = function () {
//             // websocket is closed.
//             alert("Connection is closed...");
//         };
//     }
//
//     else {
//         // The browser doesn't support WebSocket
//         alert("WebSocket NOT supported by your Browser!");
//     }
// }
//
// $('#wyslij').click(function () {
//     WebSocketTest();
// });