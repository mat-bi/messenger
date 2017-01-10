/**
 * Created by micha on 10.01.2017.
 */

$('#register_btn').click(function (e) {
    var socket = new WebSocket("ws://127.0.0.1:3000/websocket");
    e.preventDefault();

    socket.onopen = function (event) {
        var login = $("#login").val();
        var password = $("#password").val();

        var register = {
            "type": 1,
            "login": login,
            "password": password
        };

        socket.send(JSON.stringify(register));
    };

    socket.onmessage = function (message) {
        var responseCode = JSON.parse(message.data).type;
        if(responseCode == 4) {
            toastr.error('Login is already taken!');
        } else if(responseCode == 5) {
            toastr.success('Registration successful!');
        }
    };
});

$('#login_btn').click(function (e) {
    var socket = new WebSocket("ws://127.0.0.1:3000/websocket");
    e.preventDefault();

    socket.onopen = function (event) {
        var login = $("#log").val();
        var password = $("#pass").val();

        var log = {
            "type": 0,
            "login": login,
            "password": password
        };

        socket.send(JSON.stringify(log));
    };

    socket.onmessage = function (message) {
        var responseCode = JSON.parse(message.data).type;
        if(responseCode == 2) {
            toastr.error('Wrong login and/or password!');
        } else if(responseCode == 3) {
            toastr.success("Logged in successfully!");
        }
    };
});