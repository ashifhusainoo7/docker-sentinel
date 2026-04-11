"""DockerSentinel Agent — Lightweight container that monitors local Docker events.

Usage:
    docker run -v /var/run/docker.sock:/var/run/docker.sock \
        dockersentinel/agent --token YOUR_API_KEY --url wss://your-sentinel.com/api/v1/ws/agent

The agent:
1. Connects to the local Docker socket
2. Authenticates to DockerSentinel platform via API key
3. Listens for die/oom/kill events
4. Streams crash events back to the platform via WebSocket
"""

import argparse
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("sentinel.agent")


def main():
    parser = argparse.ArgumentParser(description="DockerSentinel Agent")
    parser.add_argument("--token", required=True, help="API key for authentication")
    parser.add_argument(
        "--url",
        default="ws://localhost:8000/api/v1/ws/agent",
        help="WebSocket URL of the DockerSentinel platform",
    )
    parser.add_argument(
        "--docker-socket",
        default="/var/run/docker.sock",
        help="Path to Docker socket",
    )
    args = parser.parse_args()

    logger.info("DockerSentinel Agent starting...")
    logger.info("Platform URL: %s", args.url)
    logger.info("Docker socket: %s", args.docker_socket)

    # Placeholder — full implementation will:
    # 1. Connect to local Docker socket via Docker SDK
    # 2. Establish WebSocket connection to platform (with API key auth)
    # 3. Listen for Docker die/oom/kill events
    # 4. For each event: pull last 200 log lines, construct CrashEvent JSON
    # 5. Send CrashEvent over WebSocket
    # 6. Handle reconnection on disconnect
    raise NotImplementedError(
        "Agent event streaming not yet implemented. "
        "Will use docker.DockerClient for local events "
        "and websockets library to stream to platform."
    )


if __name__ == "__main__":
    main()
