import socket
import threading
import time

HOST = "127.0.0.1"
PORT = 55614

# List stores all clients connected to the server
clients = []

# Dictionary that logs the latest activity time of each client
latest_activity = {}

# Threading lock used for safer handling of the 'clients' list and 'latest_activity' dict
clients_lock = threading.Lock()

# List stores all client usernames
usernames: list[str] = []


def broadcast(message, exclude_socket=None) -> None:
    """Broadcasts message to all connected clients.
    The 'exclude_socket'-parameter allows for excluding a client socket from the broadcast."""

    with clients_lock:
        print(f"Broadcasting message: {message.decode("utf-8")}")
        # Loops through all connected clients
        for client in clients:
            # Attempts to send the message to all but the excluded client (if one is specified)
            if client != exclude_socket:
                try:
                    client.send(message)
                except BrokenPipeError:
                    remove_client(client)


def start_server() -> None:
    """Starts the server and and accepts new client connections."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((HOST, PORT))  # Binds the server to local host
        server_socket.listen()  # Enables server to accept incoming client connections
        print(f"Server listening on socket address {HOST}:{PORT}")

        # Creates and starts the idle time thread to check for idle clients
        idle_time_thread = threading.Thread(target=check_idle_time)
        idle_time_thread.start()

        while True:
            # Retrieve client socket and address
            client_socket, client_addr = server_socket.accept()
            print(f"Connected with {str(client_addr)}")

            client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

            # Retrieves username from client
            client_socket.send("USERNAME_REQUEST".encode("utf-8"))
            username = client_socket.recv(1024).decode("utf-8")
            usernames.append(username)

            # Safely adds the client to the 'clients' list and logs the time of this activity
            with clients_lock:
                clients.append(client_socket)
                latest_activity[client_socket] = time.time()

            # Informs the client that it has successfully connected to the server
            client_socket.send("CLIENT_CONNECTED".encode("utf-8"))

            # Broadcasts that a new user has entered the chat in green color
            broadcast(f"GREEN!\n'{username}' just entered the chat!\n".encode("utf-8"), exclude_socket=client_socket)

            # Creates and starts a new thread that handles each client connection
            thread = threading.Thread(target=handle_client, args=(client_socket,))
            thread.start()


def handle_client(client_socket) -> None:
    """Handles the connection with a client. Removes client when cleanly disconnected."""
    while True:
        try:
            # Receives and decodes message from client
            message = client_socket.recv(1024).decode("utf-8")

            # Logs the time of the latest message sent by the client
            with clients_lock:
                latest_activity[client_socket] = time.time()

            # Removes the client if it has cleanly disconnected
            if not message:
                remove_client(client_socket)
                break

            # Sends received message to all other clients in blue color
            broadcast(f"BLUE!{message}".encode("utf-8"), exclude_socket=client_socket)

        except Exception as e:
            print(f"Something went wrong with the connection. Error message: {e}")
            remove_client(client_socket)
            break


def check_idle_time() -> None:
    """Checks every five seconds to see if a client has been idle for more than two minutes.
    Disconnects the client if that is the case."""
    while True:
        time.sleep(5)

        # Will store any potential idle clients that will be removed
        clients_to_remove = []

        with clients_lock:
            # Loops through all clients to check their idle times
            for client in clients:
                # Calculates the idle time
                idle_time = time.time() - latest_activity[client]

                # Appends client to removal list if idle for more than two minutes
                if idle_time > 120:
                    client.send("IDLE_TIMEOUT".encode("utf-8"))
                    clients_to_remove.append(client)

        # Removes all idle clients
        for client in clients_to_remove:
            remove_client(client)


def remove_client(client_socket) -> None:
    """Removes a client and its username from the 'clients' and 'usernames' lists."""

    username = ""

    with clients_lock:
        if client_socket in clients:
            try:
                client_index = clients.index(client_socket)  # Finds index of client
                username = usernames[client_index]  # Gets the username

                clients.remove(client_socket)  # Removes client from 'clients' list
                usernames.remove(username)  # Removes the username from 'users' list
                del latest_activity[client_socket]  # Removes the idle time logging data from 'latest_activity' dict
                client_socket.close()  # Closes the socket

            except ValueError:
                print("Client already removed")

    # Broadcasts that user has left the chat after the lock has been released (to avoid deadlock)
    if username:
        print(f"Broadcasting message: 'User '{username}' just left the chat!'")
        # Informs all other clients that the user has disconnected from the server in red color
        broadcast(f"RED!\n'{username}' just left the chat!\n".encode("utf-8"))


if __name__ == "__main__":
    start_server()
