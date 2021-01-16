from __future__ import annotations

import time

from typing import List

from bs4 import BeautifulSoup

from instascrape.core._mappings import _PostMapping, _ProfileMapping
from instascrape.core._static_scraper import _StaticHtmlScraper
from instascrape.scrapers.post import Post

class Profile(_StaticHtmlScraper):
    """Scraper for an Instagram profile page"""

    _Mapping = _ProfileMapping

    def get_recent_posts(self, amt: int = 12) -> List[Post]:
        """
        Return a list of the profiles recent posts. Max available for return
        is 12.

        Parameters
        ----------
        amt : int
            Amount of recent posts to return

        Returns
        -------
        posts : List[Post]
            List containing the recent 12 posts and their available data
        """
        if amt > 12:
            raise IndexError(
                f"{amt} is too large, 12 is max available posts. Getting more posts will require an out-of-the-box extension."
            )
        posts = []
        try:
            post_arr = self.json_dict["entry_data"]["ProfilePage"][0]["graphql"]["user"][
                "edge_owner_to_timeline_media"
            ]["edges"]
        except TypeError:
            raise ValueError(
                "Can't return posts without first scraping the Profile. Call the scrape method on your object first."
            )

        for post in post_arr[:amt]:
            json_dict = post["node"]
            mapping = _PostMapping.post_from_profile_mapping()
            post = Post(json_dict)
            post.scrape(mapping=mapping)
            posts.append(post)
        return posts

    def get_posts(self, webdriver, amt_posts=None, login_first=False, login_pause=60, max_failed_scroll=300, scrape=False, scrape_pause=5):
        """Return unscraped Post objects from a Profile"""
        JS_SCROLL_SCRIPT = "window.scrollTo(0, document.body.scrollHeight); var lenOfPage=document.body.scrollHeight; return lenOfPage;"
        JS_PAGE_LENGTH_SCRIPT = "var lenOfPage=document.body.scrollHeight; return lenOfPage;"
        try:
            posts_len = self.posts
        except AttributeError:
            raise AttributeError(f"{type(self)} must be scraped first")

        if login_first:
            webdriver.get("https://www.instagram.com")
            time.sleep(login_pause)

        webdriver.get(self.url)

        posts = []
        shortcodes = []
        scroll_attempts = 0
        last_position = webdriver.execute_script(JS_PAGE_LENGTH_SCRIPT)
        while scroll_attempts < max_failed_scroll:
            print(True)
            current_position = webdriver.execute_script(JS_SCROLL_SCRIPT)
            source_data = webdriver.page_source
            found_posts = self._separate_posts(source_data)

            for post in found_posts:
                if post.source not in shortcodes:
                    shortcodes.append(post.source)
                    posts.append(post)

            if len(posts) == posts_len:
                break
            if current_position == last_position:
                print("FAIL ATTEMPT")
                scroll_attempts += 1
            else:
                scroll_attempts = 0
                last_position = current_position

        scraped_posts = []
        if scrape:
            for post in posts:
                scraped_posts.append(post.scrape(inplace=False, webdriver=webdriver))
                time.sleep(scrape_pause)
            posts = scraped_posts

        return posts

    def _separate_posts(self, source_data):
        """Separate the HTML and parse out BeautifulSoup for every post"""
        post_soup = []

        soup = BeautifulSoup(source_data, features="lxml")
        anchor_tags = soup.find_all("a")
        post_tags = [tag for tag in anchor_tags if tag.find(
            "div", {"class": "eLAPa"})]

        #Filter new posts that have not been stored yet
        new_posts = [tag for tag in post_tags if tag not in post_soup]
        post_soup += new_posts

        return self._create_post_objects(post_soup)

    def _create_post_objects(self, post_soup):
        """Create a Post object from the given shortcode"""
        posts = []
        for post in post_soup:
            shortcode = post["href"].replace("/p/", "")[:-1]
            posts.append(Post(shortcode))
        return posts

    def _url_from_suburl(self, suburl):
        return f"https://www.instagram.com/{suburl}/"
