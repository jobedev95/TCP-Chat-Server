import socket
import threading
import pyinputplus as py
from colorama import Fore
import time

HOST = "127.0.0.1"
PORT = 55614

# Dictionary with colors for the prints
colors: dict[str, str] = {
    "RED": Fore.RED,
    "GREEN": Fore.GREEN,
    "BLUE": Fore.BLUE,
    "YELLOW": Fore.YELLOW,
    "WHITE": Fore.WHITE,
    "RESET": Fore.RESET,
}

# Flag used to inform both threads if the socket has been closed
socket_is_closed = False


def receive_messages(client_socket, username) -> None:
    """Receives messages sent from the server.
    If the server sends "USERNAME_REQUEST" the client will respond with the clients username."""
    global socket_is_closed

    while True:
        try:
            # Receives data from the server and decodes it
            message = client_socket.recv(1024).decode("utf-8")

            # Informs client that it has successfully connected to the server
            if message == "CLIENT_CONNECTED":
                print(colors["GREEN"] + "Connected to the chat server. You can start chatting!" + colors["RESET"])
                print(colors["YELLOW"] + "You can leave the chat at any time by entering 'exit'.\n" + colors["RESET"])

            # Sends the username to server when requested
            elif message == "USERNAME_REQUEST":
                client_socket.send(username.encode("utf-8"))

            # If idle for more than 120 seconds the socket will be closed
            elif message == "IDLE_TIMEOUT":
                print(colors["RED"] + "\nYou have been idle for too long. You have been disconnected." + colors["RESET"])
                socket_is_closed = True
                client_socket.close()
                break

            # Else it prints the received message in the given color
            else:
                # All messages from the server will contain the color and the message separated by an exclamation mark "!" (eg. 'BLUE!message')
                # Here the color and the message itself gets separated into two before the content gets printed
                color, content = message.split("!", 1)
                print(colors[color] + content + colors["RESET"])

        # Closes the connection if an error occurs
        except Exception as e:
            # If the user closed the chat the exception will be handled by breaking the loop
            if socket_is_closed:
                break

            # All other exceptions will print the given error in red and close the socket
            print(colors["RED"] + f"\nAn error occurred! Error message: {e}" + colors["RESET"])
            client_socket.close()
            break


def send_messages(client_socket, username) -> None:
    """Handles the clients input and sends it to the server.
    If the client sends 'exit' it ends the loop and the client disconnects."""

    global socket_is_closed

    while not socket_is_closed:
        try:
            time.sleep(2)  # Timer ensuring that the client cannot spam the server
            message = py.inputStr()  # Takes the message from the user

            # Closes the socket if user enters 'exit'
            if message.lower() == "exit":
                socket_is_closed = True
                client_socket.close()  # Closes the socket
                break
            else:
                message = f"{username}: {message}"

            # Sends the message to the server
            client_socket.send(message.encode("utf-8"))
        except Exception as e:
            if socket_is_closed:
                print(colors["RED"] + "Cannot send more messages. You have been disconnected." + colors["RESET"])
                break
            print(f"Error when attempting to send the message. Error message: {e}")
            break


def start_client() -> None:
    """Asks the user for a username and connects to the main server."""

    # Gets the username and ensures that it only contains letters A-Z
    username = py.inputRegex(
        prompt="Enter you username: ",
        regex=r"^[A-Za-z]+$",
    ).upper()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        client_socket.connect((HOST, PORT))  # Connects to the server

        # Creates and starts a thread to receive messages from the server
        receive_thread = threading.Thread(target=receive_messages, args=(client_socket, username))
        receive_thread.start()

        # Creates and starts a thread to send messages to the server
        send_thread = threading.Thread(target=send_messages, args=(client_socket, username))
        send_thread.start()

        # Waits for both threads to finish before the main thread continues
        send_thread.join()
        receive_thread.join()


if __name__ == "__main__":
    start_client()
