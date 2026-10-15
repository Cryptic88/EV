import json


class ToolRegistry:

    def __init__(
        self,
        application_tools,
        volume_tools,
        web_tools
    ):

        self.application_tools = application_tools
        self.volume_tools = volume_tools
        self.web_tools = web_tools

        self.functions = {

            "close_program":
                self.application_tools.close_program,

            "open_program":
                self.application_tools.open_program,

            "close_browser_tab":
                self.application_tools.close_browser_tab,

            "open_browser_tab":
                self.application_tools.open_browser_tab,

            "browser_search":
                self.application_tools.browser_search,

            "set_volume":
                self.volume_tools.set_volume,

            "change_volume":
                self.volume_tools.change_volume,

            "mute_volume":
                self.volume_tools.mute_volume,

            "search_web":
                self.web_tools.search_web,

            "read_webpage":
                self.web_tools.read_webpage,
        }

    # ============================================================
    # TOOL DEFINITIONS
    # ============================================================

    def get_tools(self):

        return [

            # ----------------------------------------------------
            # OPEN PROGRAM
            # ----------------------------------------------------

            {
                "type": "function",
                "function": {
                    "name": "open_program",
                    "description": (
                        "Open or launch an application "
                        "on the user's computer."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "process_name": {
                                "type": "string",
                                "description": (
                                    "Application to open, "
                                    "for example WhatsApp, Outlook, "
                                    "Visual Studio Code, Android Studio, "
                                    "Notepad, or Spotify."
                                )
                            }
                        },
                        "required": [
                            "process_name"
                        ]
                    }
                }
            },

            # ----------------------------------------------------
            # CLOSE PROGRAM
            # ----------------------------------------------------

            {
                "type": "function",
                "function": {
                    "name": "close_program",
                    "description": (
                        "Close a running application "
                        "on the user's computer."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "process_name": {
                                "type": "string",
                                "description": (
                                    "Application to close."
                                )
                            }
                        },
                        "required": [
                            "process_name"
                        ]
                    }
                }
            },

            # ----------------------------------------------------
            # OPEN BROWSER TAB
            # ----------------------------------------------------

            {
                "type": "function",
                "function": {
                    "name": "open_browser_tab",
                    "description": (
                        "Open a URL in a new browser tab "
                        "using the user's default browser."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": (
                                    "Full URL to open."
                                )
                            }
                        },
                        "required": [
                            "url"
                        ]
                    }
                }
            },

            # ----------------------------------------------------
            # BROWSER SEARCH
            # ----------------------------------------------------

            {
                "type": "function",
                "function": {
                    "name": "browser_search",
                    "description": (
                        "Open a supported website in the "
                        "default browser and perform a search "
                        "for the user's requested query. "
                        "Use this when the user asks to open "
                        "a website and search for something "
                        "on that website. Supported websites "
                        "currently include YouTube, Google, "
                        "and Bing."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "site": {
                                "type": "string",
                                "description": (
                                    "Website to search. "
                                    "Examples: youtube, "
                                    "google, bing."
                                )
                            },
                            "query": {
                                "type": "string",
                                "description": (
                                    "The exact thing the "
                                    "user wants to search for."
                                )
                            }
                        },
                        "required": [
                            "site",
                            "query"
                        ]
                    }
                }
            },

            # ----------------------------------------------------
            # CLOSE BROWSER TAB
            # ----------------------------------------------------

            {
                "type": "function",
                "function": {
                    "name": "close_browser_tab",
                    "description": (
                        "Close a browser tab whose title "
                        "matches the provided keywords."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "tab_keywords": {
                                "type": "string",
                                "description": (
                                    "Keyword or comma-separated "
                                    "keywords appearing in "
                                    "the tab title."
                                )
                            }
                        },
                        "required": [
                            "tab_keywords"
                        ]
                    }
                }
            },

            # ----------------------------------------------------
            # SEARCH WEB
            # ----------------------------------------------------

            {
                "type": "function",
                "function": {
                    "name": "search_web",
                    "description": (
                        "Search the internet for information, "
                        "news, facts, or current information. "
                        "This is for retrieving information, "
                        "not for controlling a browser."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": (
                                    "Search query."
                                )
                            }
                        },
                        "required": [
                            "query"
                        ]
                    }
                }
            },

            # ----------------------------------------------------
            # READ WEBPAGE
            # ----------------------------------------------------

            {
                "type": "function",
                "function": {
                    "name": "read_webpage",
                    "description": (
                        "Read the text content of a specific "
                        "webpage."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": (
                                    "Full URL of the webpage."
                                )
                            }
                        },
                        "required": [
                            "url"
                        ]
                    }
                }
            },

            # ----------------------------------------------------
            # SET VOLUME
            # ----------------------------------------------------

            {
                "type": "function",
                "function": {
                    "name": "set_volume",
                    "description": (
                        "Set system volume from 0 to 100."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "level": {
                                "type": "integer",
                                "description": (
                                    "Volume level 0-100."
                                )
                            }
                        },
                        "required": [
                            "level"
                        ]
                    }
                }
            },

            # ----------------------------------------------------
            # CHANGE VOLUME
            # ----------------------------------------------------

            {
                "type": "function",
                "function": {
                    "name": "change_volume",
                    "description": (
                        "Increase or decrease system volume."
                    ),
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
                                "description": (
                                    "Percentage points "
                                    "to change."
                                )
                            }
                        },
                        "required": [
                            "direction"
                        ]
                    }
                }
            },

            # ----------------------------------------------------
            # MUTE
            # ----------------------------------------------------

            {
                "type": "function",
                "function": {
                    "name": "mute_volume",
                    "description": (
                        "Mute or unmute system audio."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "mute": {
                                "type": "boolean"
                            }
                        },
                        "required": [
                            "mute"
                        ]
                    }
                }
            }
        ]

    # ============================================================
    # EXECUTE TOOL
    # ============================================================

    def execute(
        self,
        function_name,
        arguments
    ):

        function = self.functions.get(
            function_name
        )

        if not function:

            return (
                f"Unknown tool: "
                f"{function_name}"
            )

        try:

            return function(
                **arguments
            )

        except Exception as error:

            return (
                f"Tool '{function_name}' "
                f"failed: {error}"
            )
