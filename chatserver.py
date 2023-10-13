import socket
import threading
import time

clients = {}
clients_last_alive = {}
clients_lock = threading.Lock()

# Set the timeout interval for receiving "Alive" messages (in seconds)
ALIVE_TIMEOUT = 10

def handle_client(client_socket, client_id):
    global clients, clients_last_alive
    while True:
        try:
            message = client_socket.recv(1024).decode('utf-8')

            if not message:
                remove_client(client_id, client_socket)
                break

            if message == 'Alive':
                # Handle Alive message from client
                reset_client_life(client_id)
            elif message.startswith('@Quit'):
                remove_client(client_id, client_socket)
                break
            elif message.startswith('@List'):
                send_client_list(client_socket)
            elif message.startswith('('):
                target_client_id, msg_content = parse_message(message)
                if target_client_id and msg_content:
                    send_message(client_id, target_client_id, msg_content, client_socket)
        except:
            remove_client(client_id, client_socket)
            break

def parse_message(message):
    # Parse the general message format: (target_client_id) message-content
    if message.startswith('(') and ')' in message:
        start_idx = message.index('(') + 1
        end_idx = message.index(')')
        target_client_id = message[start_idx:end_idx]
        msg_content = message[end_idx + 1:].strip()
        return target_client_id, msg_content
    return None, None

def send_client_list(client_socket):
    global clients
    with clients_lock:
        client_list = ', '.join(list(clients.keys()))
        client_socket.send(client_list.encode('utf-8'))

def send_message(source_client_id, target_client_id, message_content, client_socket):
    global clients
    with clients_lock:
        if target_client_id in clients:
            target_client_socket = clients[target_client_id]
            formatted_message = f'received from client ({source_client_id}): {message_content}'
            target_client_socket.send(formatted_message.encode('utf-8'))
        else:
            # Notify the source client that the target client is not online
            offline_message = f'Client {target_client_id} is not online.'
            client_socket.send(offline_message.encode('utf-8'))

def send_client_list_to_all_clients():
    global clients

    # Create a single message with the list of online clients
    online_clients_message = f'Online clients: {", ".join(list(clients.keys()))}'

    # Send the message to all clients
    for client_id, client_socket in clients.items():
        client_socket.send(online_clients_message.encode('utf-8'))

def reset_client_life(client_id):
    global clients_last_alive
    with clients_lock:
        clients_last_alive[client_id] = time.time()
        
        # Create a list of online clients
        online_clients = list(clients.keys())
        
        # Create a single message with the list of online clients
        online_clients_message = f'Online clients: {", ".join(online_clients)}'
        
        # Print the online clients message
        print(f"Alive: {client_id} - {online_clients_message}")


def remove_client(client_id, client_socket):
    global clients, clients_last_alive
    with clients_lock:
        if client_id in clients:
            del clients[client_id]
            del clients_last_alive[client_id]
            client_socket.close()  # Close the client socket
            print(
                f'Client {client_id} disconnected. Online clients: {list(clients.keys())}')
            send_client_list_to_all_clients()

def check_client_alive():
    global clients_last_alive
    while True:
        current_time = time.time()
        clients_to_remove = []
        with clients_lock:
            for client_id, last_alive_time in clients_last_alive.items():
                if current_time - last_alive_time > ALIVE_TIMEOUT:
                    clients_to_remove.append(client_id)
        for client_id in clients_to_remove:
            client_socket = clients.get(client_id)
            if client_socket:
                client_socket.close()  # Close the socket before removing the client
            remove_client(client_id, client_socket)
        time.sleep(1)  # Check client activity every 1 second

def main():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('localhost', 12345))
    server_socket.listen(5)

    print('Server listening on port 12345...')

    alive_check_thread = threading.Thread(target=check_client_alive)
    alive_check_thread.start()

    while True:
        client_socket, addr = server_socket.accept()
        client_id = client_socket.recv(1024).decode('utf-8')
        with clients_lock:
            clients[client_id] = client_socket
            clients_last_alive[client_id] = time.time()
            print(
                f'Client {client_id} connected. Online clients: {list(clients.keys())}')
            send_client_list_to_all_clients()
            
        client_handler = threading.Thread(
            target=handle_client, args=(client_socket, client_id))
        client_handler.start()

if __name__ == "__main__":
    main()
