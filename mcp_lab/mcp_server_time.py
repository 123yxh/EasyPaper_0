from mcp.server.fastmcp import FastMCP
from datetime import datetime
import pytz
from typing import Optional

# Initialize FastMCP server with configuration
mcp = FastMCP(
    "TimeService",  # Name of the MCP server
    instructions="You are a time assistant that can provide the current time for different timezones.",  # Instructions for the LLM on how to use this tool
    host="0.0.0.0",  # Host address (0.0.0.0 allows connections from any IP)
    port=8005,  # Port number for the server
)


@mcp.tool()
async def get_current_time(timezone: Optional[str] = "Asia/Seoul") -> str:
    """
    Get current time information for the specified timezone.

    This function returns the current system time for the requested timezone.

    Args:
        timezone (str, optional): The timezone to get current time for. Defaults to "Asia/Seoul".

    Returns:
        str: A string containing the current time information for the specified timezone
    """
    try:
        # Get the timezone object
        tz = pytz.timezone(timezone)

        # Get current time in the specified timezone
        current_time = datetime.now(tz)

        # Format the time as a string
        formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S %Z")

        return f"Current time in {timezone} is: {formatted_time}"
    except pytz.exceptions.UnknownTimeZoneError:
        return f"Error: Unknown timezone '{timezone}'. Please provide a valid timezone."
    except Exception as e:
        return f"Error getting time: {str(e)}"


if __name__ == "__main__":
    # Start the MCP server with stdio transport
    # stdio transport allows the server to communicate with clients
    # through standard input/output streams, making it suitable for
    # local development and testing
    mcp.run(transport="stdio")
