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
        var responseCode = JSON.parse(message.data).type;
        if (responseCode == 2) {
            toastr.error('Wrong login and/or password!');
        } else if (responseCode == 3) {
            toastr.success("Logged in successfully!");
        } else if (responseCode == 4) {
            toastr.error('Login is already taken!');
        } else if (responseCode == 5) {
            toastr.success('Registration successful!');
        }
    };
});