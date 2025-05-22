from IPython.display import display, HTML

html_code = """
<div>
  <h3>WebSocket Streamed Data:</h3>
  <div id="output" style="border: 1px solid #ccc; padding: 10px; height: 200px; overflow-y: auto;"></div>
  <button onclick="sendMessage()">Start Process</button>
</div>

<script>
  let socket;
  const outputDiv = document.getElementById("output");

  function connectWebSocket() {
    socket = new WebSocket("wss://your-gateway-url/ws/simulation");

    socket.onopen = function() {
      console.log("WebSocket connected.");
    };

    socket.onmessage = function(event) {
      const data = JSON.parse(event.data);
      const para = document.createElement("p");
      para.textContent = JSON.stringify(data);
      outputDiv.appendChild(para);
    };

    socket.onclose = function() {
      console.log("WebSocket closed.");
    };

    socket.onerror = function(err) {
      console.error("WebSocket error:", err);
    };
  }

  function sendMessage() {
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      connectWebSocket();
      // Wait for socket to open before sending
      socket.addEventListener("open", () => {
        socket.send(JSON.stringify({ action: "start", token: "YOUR_AUTH_TOKEN" }));
      });
    } else {
      socket.send(JSON.stringify({ action: "start", token: "YOUR_AUTH_TOKEN" }));
    }
  }
</script>
"""

display(HTML(html_code))
