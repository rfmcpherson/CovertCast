This code is the shim/proxy in between the browser and CovertCast on
the client side and between the rest of the Internet and CovertCast on
the server side.


clientweb.py
fixurl - Method to turn string to unicode URL
main - Opens a WebSocket connection and sends a message
ConnectionThread - Handles an individual connection with the client
WebClient - Handles HTTP on the client side
WebSocket - Handles the client-side WebSocket connection


fakeclientweb.py
fixurl - Method to turn string to unicode URL
FakeConnectionThread - Handles an individual connection with the client
FakeWebClient - A fake HTTP client for testing. Fakes the CovertCast
              client and returns presaved files


httpsclientweb.py
fixurl - Method to turn string to unicode URL
ConnectionThread - Handles individual sockets from the browser
DummyWebSocket - Dummy WebSocket wrapper class used for testing
HTTPSWebClient - Handles HTTPS on client side 
WebSocket - Handles the client-side WebSocket connection


httpsserverweb.py
ConnectionThread - Handles individual sockets from the browser
ConnectionWorker - Compresses and sends back response
DummyWebSocket - Dummy WebSocket wrapper class for testing
HTTPSWebSocket - Handles HTTPS on the server side


serverweb.py
ConnectionThread - Handles individual sockets from the browser
ConnectionWorker - Compresses and sends back response
WebSocket - Handles HTTP on the server side

