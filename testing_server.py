
import socket


def handle_method(method, conn, addr, request, chatlog):
    print ('Connected by', addr)
    print ('Request is:', request)

    if method == "GET":
        content = text_content.encode()
        conn.sendall(content)

    if method == "POST":
        print("Got post request")
        print("Extraced message:",message)



def chatlog_to_text(chatlog):
    text = ""
    for msg in chatlog:
        text = str(msg) + "\n"
    return text

def run_server(PORT):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("",PORT))
    print("Listening")
    chatlog = []

    while True:
        sock.listen(3)
        conn, addr = sock.accept()
        request = conn.recv(1024).decode() # Accept a message w length 1024
        method = request.split(" ")[0] # Part 1
        src = request.split(" ")[1] # Part 2?

        handle_method(method, conn, addr ,request, chatlog)

        # close connection
        conn.close()

# with socketserver.TCPServer(("localhost",PORT), handler) as httpd:
#     print("serving port", PORT)
#     httpd.serve_forever()




# Run here
if __name__ == "__main__":
    p = 8888
    run_server(p)