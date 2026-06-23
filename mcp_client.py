import asyncio
import os
import sys
import argparse
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def run_client(tool_name=None, tool_args=None):
    # Construct paths relative to this script's directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    server_path = os.path.join(current_dir, "mcp_server.py")
    
    # Define server start parameters using the current python executable to preserve virtualenv
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[server_path],
        env=os.environ.copy() # Inherit DB environment variables
    )
    
    print(f"Connecting to GICS MCP Server at {server_path}...")
    try:
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                # Initialize connection
                await session.initialize()
                print("SUCCESS: Connected & initialized session.")
                print("-" * 50)
                
                # Fetch available tools
                result = await session.list_tools()
                tools = result.tools
                
                # If no specific tool is requested, run interactively
                if not tool_name:
                    print("Available tools in GICS MCP Server:")
                    for t in tools:
                        print(f" - {t.name}: {t.description.strip()}")
                    print("-" * 50)
                    print("Interactive Mode. Type 'exit' to quit.")
                    
                    while True:
                        try:
                            user_input = input("\nEnter tool name to call (or 'help'/'exit'): ").strip()
                            if not user_input or user_input.lower() == 'exit':
                                break
                            if user_input.lower() == 'help':
                                print("Available tools:")
                                for t in tools:
                                    print(f"  {t.name}: {t.description.strip()}")
                                continue
                            
                            # Find the tool
                            target_tool = next((t for t in tools if t.name == user_input), None)
                            if not target_tool:
                                print(f"Error: Tool '{user_input}' not found. Type 'help' to see list.")
                                continue
                            
                            # Ask for parameters based on schema
                            args = {}
                            schema = target_tool.inputSchema
                            properties = schema.get("properties", {})
                            required_fields = schema.get("required", [])
                            
                            if properties:
                                print(f"Parameters for '{target_tool.name}':")
                                for prop_name, prop_info in properties.items():
                                    req_marker = " (required)" if prop_name in required_fields else " (optional)"
                                    val = input(f"  {prop_name} [{prop_info.get('type')}] {req_marker}: ").strip()
                                    if val:
                                        if prop_info.get('type') == 'integer':
                                            args[prop_name] = int(val)
                                        else:
                                            args[prop_name] = val
                                    elif prop_name in required_fields:
                                        print(f"  Warning: '{prop_name}' is required but left blank.")
                            
                            print(f"\nCalling tool '{target_tool.name}' with arguments: {args}...")
                            call_result = await session.call_tool(target_tool.name, arguments=args)
                            
                            print("\n[Tool Output Response]:")
                            for content in call_result.content:
                                if getattr(content, 'text', None):
                                    print(content.text)
                                else:
                                    print(content)
                        except KeyboardInterrupt:
                            print("\nExiting interactive mode...")
                            break
                        except Exception as e:
                            print(f"Error during tool call: {str(e)}")
                else:
                    # Non-interactive command-line execution
                    target_tool = next((t for t in tools if t.name == tool_name), None)
                    if not target_tool:
                        print(f"Error: Tool '{tool_name}' not found.")
                        return
                    
                    parsed_args = {}
                    if tool_args:
                        # Parse simple key=value arguments passed from CLI
                        for arg in tool_args:
                            if '=' in arg:
                                k, v = arg.split('=', 1)
                                parsed_args[k] = v
                                
                    print(f"Calling tool '{tool_name}' with args {parsed_args}...")
                    call_result = await session.call_tool(tool_name, arguments=parsed_args)
                    
                    print("\n[Tool Output Response]:")
                    for content in call_result.content:
                        if getattr(content, 'text', None):
                            print(content.text)
                        else:
                            print(content)
                            
    except Exception as e:
        print(f"FATAL ERROR connecting to MCP server: {str(e)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test MCP Client for GICS Classification Server")
    parser.add_argument("tool", nargs="?", help="Optional: Name of the tool to execute")
    parser.add_argument("args", nargs="*", help="Optional: Arguments for the tool in key=value format (e.g. ticker=AAPL)")
    
    args = parser.parse_args()
    
    # Run the client
    asyncio.run(run_client(args.tool, args.args))
