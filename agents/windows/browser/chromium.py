"""
Interact with Microsoft Edge.
"""

import logging
from typing import Literal

import rpyc
from playwright.sync_api import BrowserContext, sync_playwright
from util import get_appdata_local_path

logger = logging.getLogger(__name__)


# ignore: mypy does not recognize the `rpyc.Service` class
class ChromiumService(rpyc.Service):  # type: ignore[misc]
    """
    Allows you to interact with a Microsoft Edge browser instance.

    Use the `EdgeServiceAPI` class to connect to and interact with this service.

    TODO: can't this just be generalized to allow for any browser?
    """

    def on_connect(self, conn: rpyc.Connection) -> None:
        """
        Start the Playwright instance when a connection is made.

        Expose both the Playwright instance and the browser context to the client.
        """
        self.playwright = sync_playwright().start()
        self.browser: BrowserContext | None = None

    def on_disconnect(self, conn: rpyc.Connection) -> None:
        """
        Close the browser and stop the Playwright instance when the connection
        is closed.
        """
        if self.browser is not None:
            self.browser.close()
            self.browser = None

        self.playwright.stop()

    def exposed_set_browser(
        self, browser_type: Literal["msedge", "chrome"], profile: str = "Default"
    ) -> BrowserContext:
        """
        Set the browser to use for this service.

        :param browser: The browser to use (which corresponds to the distribution
            channel).
        :param profile: The profile to use for the browser. Defaults to "Default".
            Note that the profile must already exist.
        """
        if self.browser is not None:
            self.browser.close()
            self.browser = None

        if browser_type == "chrome":
            # Use the Chrome profile path
            profile_path = get_appdata_local_path() / "Google" / "Chrome" / "User Data"
        elif browser_type == "msedge":
            # Use the Edge profile path
            profile_path = get_appdata_local_path() / "Microsoft" / "Edge" / "User Data"
        else:
            raise ValueError(f"Unsupported browser type: {browser_type}")

        chromium = self.playwright.chromium
        self.browser = chromium.launch_persistent_context(
            headless=False,
            user_data_dir=profile_path,
            channel=browser_type,
            args=[f"--profile-directory={profile}"],
        )

        return self.browser


if __name__ == "__main__":
    # cd agents/windows
    # python -m browser.chromium

    # Start the server for testing. All attributes of the service are exposed,
    # since we assume that connections are trusted.
    #
    # TODO: should this actually be OneShotServer instead? again, this is based
    # on whether or not it makes sense to have a single dispatch server, as well
    # as how such a server would work
    from rpyc.utils.server import ThreadedServer

    t = ThreadedServer(
        ChromiumService, port=18861, protocol_config={"allow_all_attrs": True}
    )
    print("Starting Chromium service on port 18861")
    t.start()
