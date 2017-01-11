/**
 * Created by micha on 10.01.2017.
 */
$(document).ready(function () {
    var socker;
    $(".wrapper").hide();
    var socket = new WebSocket("ws://"+window.location.host+"/websocket");

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
        socket.send(JSON.stringify({"type" : 9}));
    });

    $("#add_friend_text").on('input',function () {
       var user = $(this).val();
        socket.send(JSON.stringify({"type": 7, "login": user}))
    });

    var friend_function = function () {
        var friendLogin = $("#add_friend_text").val();
        if (friendLogin.replace(/\s/g, "") == "") return;

        var message = {
            "type": 5,
            "login": friendLogin
        };

        socket.send(JSON.stringify(message));


        $("#add_friend_text").val('');
    };
    $("#friend_form").submit(function (e) {
        e.preventDefault();
        friend_function();
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
        socket.send(JSON.stringify({"type" : 9}));
    });

    function sendMessage(text) {
        var message = {
            "type": 2,
            "content": text
        };

        socket.send(JSON.stringify(message));

        $(".placeholder").before("<div class=\"bubble me\">" + text + "</div>");
        scrollToBottom();
        $("#text").val('');
    }

    $('#send').click(function (e) {
        e.preventDefault();
        var text = $("#text").val();
        if (text.replace(/\s/g, "") == "") return;

        sendMessage(text);
    });

    $('#text').on('keypress', function (e) {
        var text = $("#text").val();
        if (text.replace(/\s/g, "") == "") return;

        if (e.which == 13) {
            sendMessage(text);
            return false;
        }
    });

    $('#add_friend').click(friend_function);

    var addToFriendList = function (login, state) {
        var active = "Active",
            disconnected = "Disconnected";

        $(".li-placeholder").before(
            "<li class=\"person\" id=\"person_"+login+"\" data-chat=\"person2\">" +
                "<img src='" + getRandomImage() + "' alt=\"\"/>" +
                "<span class=\"name\">" + login + "<br></span>" +
                "<span class=\"time\">1:44 PM</span>" +
                "<span class=\"preview\">" + (state == 0 ? active : disconnected) + "</span>" +
            "</li>"
        );
    };

    var getRandomImage = function () {
        var images = [
            "../static/img/bob.jpg",
            "../static/img/car.jpg",
            "../static/img/cat.jpg",
            "../static/img/chess.png",
            "../static/img/doge.jpg"
        ];

        var randomNumber = Math.floor(Math.random() * 5) + 1;
        console.log(randomNumber);
        return images[randomNumber - 1];
    };

    socket.onopen = function (message) {
        console.log('open');
    };

    function scrollToBottom() {
        $('.scroll-wrapper').animate({scrollTop: $('.scroll-wrapper').prop('scrollHeight')});
    }

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
                $(".name").text(login);
                $(".wrapper").show();
                $(".module").hide();
                $(".pen-title").hide();
                break;
            case 4:
                toastr.error('Login is already taken!');
                localStorage.removeItem("currentUser");
                break;
            case 5:
                toastr.success('Registration successful!');
                $(".name").text(login);
                $(".wrapper").show();
                $(".module").hide();
                $(".pen-title").hide();
                break;

            case 7:
                toastr.info('Friend added!');
                var user = JSON.parse(message.data).user;
                $("#friends_list").empty();
                var state = (user.state == 0) ? "Active" : "Disconnected";
                $(".li-placeholder").before(
                    "<li class=\"person\" id=\"person_" + user.login + "\" data-chat=\"person2\">" +
                    "<img src=\"" + getRandomImage() + "\"/>" +
                    "<span class=\"name\">" + user.login + "<br/></span>" +
                    "<span class=\"time\">1:44 PM</span>" +
                    "<span class=\"preview\">" + state + "</span>" +
                    "</li>"
                );
                break;
            case 8:
                var user = JSON.parse(message.data);
                console.log(user);
                var state = (user.state == 0) ? "Active":"Disconnected";
                $("#person_"+user.login).children(".preview").text(state);
                var text = user.login;
                text += state == "Active" ? " came online!" : " disconnected from chat";
                toastr.info(text);
                break;
            case 9:
                var users = JSON.parse(message.data).users;
                var datalist = $("#friends_list");
                datalist.empty();
                for(var i = 0; i < users.length; i++){
                    datalist.append("<option value=\""+users[i]+"\"/>");
                }
                break;
            case 10:
                $("#friends_list").empty();
                toastr.error("No user found");
                break;
            case 12:
                if(socker === response.message.user){
                    var previousDiv = $(".placeholder").prev("div");
                    var span = $(previousDiv).find("span");
                    var text = $(span).prev().text();
                    $(span).before(text + "\n" + response.message.content);
                } else {
                    $(".placeholder").before("<div class=\"bubble you\" >" + response.message.content + "" +
                    "<span style='font-size: 10px'><br>Sent by: " + response.message.user + "</span></div>");
                }
                scrollToBottom();
                socker = response.message.user;
                break;
            case 13:
                var friends = JSON.parse(message.data).friends;
                for(var i = 0; i < friends.length; i++) {
                    addToFriendList(friends[i].login, friends[i].state);
                }
                break;
            case 14:
                localStorage.setItem("currentUser", JSON.parse(message.data).user.login);
                $('.name').text(localStorage.getItem("currentUser"));
                var msg = {"type" : 8};
                socket.send(JSON.stringify(msg));
                break;
            case 15:
                toastr.error("User doesn't exist!");
                break;
            case 16:
                toastr.error("Friendship exists!");
                break;
            case 17:
                toastr.error("You cannot add yourself as a friend!");
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