/**
 * Created by micha on 10.01.2017.
 */
$(document).ready(function () {
    var socket = new WebSocket("ws://127.0.0.1:3000/websocket");

    $('#register_btn').click(function (e) {
        e.preventDefault();

        var login = $("#login").val();
        var password = $("#password").val();

        var register = {
            "type": 1,
            "login": login,
            "password": password
        };

        socket.send(JSON.stringify(register));
    });

    $('#login_btn').click(function (e) {
        e.preventDefault();

        var login = $("#log").val();
        var password = $("#pass").val();

        var log = {
            "type": 0,
            "login": login,
            "password": password
        };

        socket.send(JSON.stringify(log));
    });

    $('#send').click(function () {
        var text = $("#text").val();
        if(text.replace(/\s/g,"") == "") return;

        var message = {
            "type": 2,
            "message": {
                "content": text
            }
        };

        socket.send(JSON.stringify(message));

        $(".placeholder").before("<div class=\"bubble me\">" + text + "</div>");
        $("#text").val('');
    });

    socket.onopen = function (message) {
        console.log('open');
    };

    socket.onmessage = function (message) {
        var response = JSON.parse(message.data);
        var responseCode = JSON.parse(message.data).type;
        switch (responseCode) {
            case 2:
                toastr.error('Wrong login and/or password!');
                break;
            case 3:
                toastr.success("Logged in successfully!");
                break;
            case 4:
                toastr.error('Login is already taken!');
                break;
            case 5:
                toastr.success('Registration successful!');
                break;
            case 12:
                $(".placeholder").before("<div class=\"bubble you\">" + response.message.content + "</div>");
                break;
            default:
                console.log('do obsluzenia');
                break;
        }
    };
});