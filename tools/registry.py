import json


class ToolRegistry:

    def __init__(
        self,
        application_tools,
        volume_tools
    ):

        self.application_tools = application_tools
        self.volume_tools = volume_tools

        self.functions = {
            "close_program":
                self.application_tools.close_program,

            "open_program":
                self.application_tools.open_program,

            "close_browser_tab":
                self.application_tools.close_browser_tab,

            "open_browser_tab":
                self.application_tools.open_browser_tab,

            "set_volume":
                self.volume_tools.set_volume,

            "change_volume":
                self.volume_tools.change_volume,

            "mute_volume":
                self.volume_tools.mute_volume,
        }

    def get_tools(self):

        return [

            {
                "type": "function",
                "function": {
                    "name": "close_program",
                    "description":
                        "Close/quit/kill a running "
                        "application on the user's computer "
                        "by name.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "process_name": {
                                "type": "string",
                                "description":
                                    "Name of the program "
                                    "to close, e.g. "
                                    "'chrome', 'spotify', "
                                    "'notepad'."
                            }
                        },
                        "required": [
                            "process_name"
                        ],
                    },
                },
            },

            {
                "type": "function",
                "function": {
                    "name": "open_program",
                    "description":
                        "Open/launch/start an application "
                        "on the user's computer by name.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "process_name": {
                                "type": "string",
                                "description":
                                    "Name of the program "
                                    "to open, e.g. "
                                    "'chrome', 'notepad', "
                                    "'calculator'."
                            }
                        },
                        "required": [
                            "process_name"
                        ],
                    },
                },
            },

            {
                "type": "function",
                "function": {
                    "name": "close_browser_tab",
                    "description":
                        "Close a specific browser tab whose title "
                        "contains one or more keyword fragments.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "tab_keywords": {
                                "type": "string",
                                "description":
                                    "Keyword fragment or comma-separated "
                                    "fragments that appear in the tab title, "
                                    "e.g. 'gmail', 'youtube,studio', or "
                                    "'project dashboard'."
                            }
                        },
                        "required": [
                            "tab_keywords"
                        ],
                    },
                },
            },

            {
                "type": "function",
                "function": {
                    "name": "open_browser_tab",
                    "description":
                        "Open a URL in a new tab using the user's default browser.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description":
                                    "Full URL to open, e.g. 'https://google.com'."
                            }
                        },
                        "required": [
                            "url"
                        ],
                    },
                },
            },

            {
                "type": "function",
                "function": {
                    "name": "set_volume",
                    "description":
                        "Set the system volume to an "
                        "exact level from 0 to 100.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "level": {
                                "type": "integer",
                                "description":
                                    "Target volume, 0-100."
                            }
                        },
                        "required": [
                            "level"
                        ],
                    },
                },
            },

            {
                "type": "function",
                "function": {
                    "name": "change_volume",
                    "description":
                        "Turn the system volume up or "
                        "down by a relative amount.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "direction": {
                                "type": "string",
                                "enum": [
                                    "up",
                                    "down"
                                ]
                            },
                            "amount": {
                                "type": "integer",
                                "description":
                                    "Percentage points "
                                    "to change. Default 10."
                            }
                        },
                        "required": [
                            "direction"
                        ],
                    },
                },
            },

            {
                "type": "function",
                "function": {
                    "name": "mute_volume",
                    "description":
                        "Mute or unmute the system volume.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "mute": {
                                "type": "boolean",
                                "description":
                                    "True to mute, "
                                    "false to unmute."
                            }
                        },
                        "required": [
                            "mute"
                        ],
                    },
                },
            },
        ]

    def execute(self, function_name, arguments):

        function = self.functions.get(
            function_name
        )

        if not function:
            return (
                f"Unknown tool: "
                f"{function_name}"
            )

        try:

            return function(**arguments)

        except Exception as error:

            return (
                f"Tool '{function_name}' "
                f"failed: {error}"
            )