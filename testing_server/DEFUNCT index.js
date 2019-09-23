const app = require('express')();
const http = require('http')
const exhttp = http.createServer(app);
const io = require('socket.io')(exhttp);

const querystring = require('querystring');
const { StringDecoder } = require('string_decoder');
const decoder = new StringDecoder('utf8');

const app2 = require('express')();
const pyhttp = http.createServer(app2);
const io2 = require('socket.io')(pyhttp);

const chatbot_address = "localhost:8887"

var PORT = 8888;
var PY_PORT = 8886;
var chatbot_api_PORT = 8881;
const py_address = "localhost:"+PY_PORT;

const cp = require("child_process");
var py_script_filepath = "../chatbot_api.py";

// Spawn a childprocess that listens for the queries from the server
// cp.exec("python3 " + py_script_filepath + ' ' + py_port + ' ', (err, stdout, stderr) =>{
//     if (stdout) {console.log(stdout)}
//     if (stderr) {console.log(stderr)}
// });
// console.log("Initiated Python chatbot API server")

var stringy = "Hello testing 一二三";
console.log(stringy)

var buffguy = Buffer.from(stringy);
console.log("buff " + buffguy)

var decoded = decoder.write(buffguy);
console.log(decoded)

app2.get('/', function(req, res){
    var msg = req.body.msg;
    console.log("python: ", msg);
})

app.get('/', function(req, res){
    res.sendFile(__dirname + '/index.html');
});

function rbt_reply(text){
    return "<机器人>:" + text;
}

io.on('connection', function(socket){
    chat_socket = socket; // GLOBAL
    var userID = socket.id;
    console.log('a user connected on ' + userID);
    var targetchatID = '';
    socket.emit('message', rbt_reply("Hello there!"));
    socket.on('chat', function(msg){
        // Self
        selfmsg = "您: " + msg;
        socket.emit('message',selfmsg);
        console.log("Requesting from backend...");
       // SEND A MESSAGE TO THE CHATBOT API
        // targetchatID, replytxt = consult_chatbot(userID, msg);
        // Doesnt return anything
        socket.emit('message',"REPLY")
      });

    socket.on('disconnect', function(){
        console.log('user disconnected');
      });
  });

exhttp.listen(PORT, function(){
    console.log('listening on: ' + PORT);
});

pyhttp.listen(PY_PORT, function(){
    console.log('listening for Python on: ' + PY_PORT);
});

io2.on('connection', function(socket){
    console.log("Connected to python server")
    python_socket = socket; // GLOBAL
    socket.on('chat reply', function(packet){
        console.log(packet)
        handle_chat_reply_packet(packet, chat_socket)
    });
    
});
function extract_reply(packet){
    reply_text = packet['message'];
    return reply_text;
}
function handle_chat_reply_packet(packet, chatsock){
    replytxt = extract_reply(packet);
    console.log("Response gotten:",replytxt);
    reply = rbt_reply(replytxt);
    chatsock.emit('chat message',reply);
}

function consult_chatbot(chatID, incoming_msg, pysock){
    var reply = "";
    var response_text = "";
    // Content
    const data_to_send = querystring.stringify ({
        'chatID': chatID,
        'msg': incoming_msg
    });

    var content = PORT + "\n" + data_to_send;

    const options = {
        host: '',
        port: chatbot_api_PORT,
        path: '/',
        method: 'GET'
    };

    // Emit via socket.io 
    pysock.emit('chat data', data_to_send)


    //Create http request
    // // Need to fix the other end somehow
    // const req = http.request(options, function(response) {
    //     console.log('Status:',response.statusCode);  
    //     response.setEncoding('utf-8')
    //     res.on('data',function(stuff){  
    //         console.log('body---------------------------------\r\n');  
    //         console.info(stuff);  
    //     });  
    //     res.on('end',function(){  
    //         console.log('No more data in response.********');  
    //     });  
    // });

    // req.on('error', (e)=>{
    //     console.error(`problem: ${e.message}`);
    // });

    // req.write(content);
    // req.end();

    if (reply === ""){
        reply = "链断了，请再发一次";
    }

    console.log("JS side GOT RESPONSE (ID:" + chatID + " reply:" + reply + ")");
    
    return chatID, reply
}
