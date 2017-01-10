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
        localStorage.setItem("currentUser", login);
        $(".name").text(login);
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
        localStorage.setItem("currentUser", login);
        $(".name").text(login);
    });

    $('#send').click(function () {
        var text = $("#text").val();
        if (text.replace(/\s/g, "") == "") return;

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

    $('#add_friend').click(function () {
        var friendLogin = $("#add_friend_text").val();
        if (friendLogin.replace(/\s/g, "") == "") return;

        var message = {
            "type": 5,
            "login": friendLogin
        };

        socket.send(JSON.stringify(message));
        $(".li-placeholder").before(
            "<li class=\"person\" data-chat=\"person2\">" +
                "<img src=\"http://s3.postimg.org/yf86x7z1r/img2.jpg\" alt=\"\"/>" +
                "<span class=\"name\">" + friendLogin + "</span>" +
                "<span class=\"time\">1:44 PM</span>" +
                "<span class=\"preview\">I've forgotten how it felt before</span>" +
            "</li>"
        );

        $("#add_friend_text").val('');
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
                localStorage.removeItem("currentUser");
                break;
            case 3:
                toastr.success("Logged in successfully!");
                break;
            case 4:
                toastr.error('Login is already taken!');
                localStorage.removeItem("currentUser");
                break;
            case 5:
                toastr.success('Registration successful!');
                break;
            case 7:
                toastr.info('Friend added!');
                break;
            case 12:
                $(".placeholder").before("<div class=\"bubble you\">" + response.message.content + "</div>");
                break;
            default:
                console.log(responseCode + '- kod do obsluzenia');
                break;
        }
    };

    socket.onclose = function (message) {
        localStorage.removeItem("currentUser");
    }
});