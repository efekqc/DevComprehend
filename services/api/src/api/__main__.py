"""Run the development API: fake learning provider, in-memory store, 127.0.0.1."""

from .server import create_server


def main():
    server = create_server()
    host, port = server.server_address
    print(f"DevComprehend API (dev/fake mode): http://{host}:{port}")
    print("Auth: Authorization: Bearer dev-token")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
