import sys
import tempfile
import subprocess

from html2text import HTML2Text
from bs4 import BeautifulSoup, Tag, PageElement


# PageElement is a generic element in the parse tree
# Tag, NavigableString, etc are all subclasses of PageElement


class CodeBlockFormatter:
    """
    Code in CPAlgorithms is formatted like
    <div class="highlight">
        <pre>
            <code>
                <span class="something">...</span>
                ...
            </code>
        </pre>
    </div>
    where in each span tag the class name identifies type of element for syntax highlighting
    (or if it is whitespace, in which case something="w") and the content is the smallest possible unit/token

    NOTE: assumes code is c++, since it uses clang-format library
    """

    @staticmethod
    def format_block(block: Tag) -> Tag:
        """
        Code block under <code> tag
        :param block: HTML <code> tag/subtree
        :return: Tag, but with content formatted
        """
        code_tokens: list[str] = []
        for i, element in enumerate(block.contents):
            if not isinstance(element, Tag) or element.name != "span":
                continue
            if element.get("class") == ["w"]:
                code_tokens.append(" ")
            else:
                code_tokens.append(element.text)
        unformatted_code = "".join(code_tokens)
        with tempfile.NamedTemporaryFile(prefix="cp_algo_", suffix=".cpp") as fpath:
            with open(fpath.name, "w") as f:
                f.write(unformatted_code)
            subprocess.call(["clang-format", "-i", f.name])  # edits in-place
            with open(fpath.name, "r") as f:
                formatted_code = f.read().strip()
        block.clear()
        block.append(f"```\n{formatted_code}\n```")
        return block

    @staticmethod
    def format_all_blocks(html: Tag) -> Tag:
        for element in html.children:
            # TODO can code come without the "pre" tag?
            if (
                    isinstance(element, Tag)
                    and element.name == "div"
                    and element.get("class") == ["highlight"]
            ):
                formatted_code_block = CodeBlockFormatter.format_block(element.pre.code)
                element.pre.clear()
                element.pre.append(formatted_code_block)
        return html


class CPAlgoParser:
    @staticmethod
    def to_markdown(html: PageElement) -> str:
        """
        Converts HTML Page element to markdown
        :param html:
        :return: markdown version of HTML Page Element
        """
        converter = HTML2Text()
        return converter.handle(str(html))

    @staticmethod
    def get_base_content(html: BeautifulSoup) -> Tag:
        """
        Extracts article tag, where main article content
        lies in the cp-algorithms webpages
        :param html:
        :return: article tag
        """
        article_tag = html.find("article")
        return article_tag

    @staticmethod
    def remove_headers_until_first_h1(article: Tag) -> Tag:
        """
        Removes all HTML elements until main title (first h1 tag).
        In cp-algorithms blogs there is usually no content before those titles
        :param article:
        :return: modified article with content before title removed
        """
        found_h1 = True
        while True:
            try:
                # we have to call iter everytime since calling extract
                # messes up the iterator (the __next__ skips one element)
                element = next(iter(article.children))
            except StopIteration:
                break
            # print(f"Element = '{element}'")
            if isinstance(element, Tag) and element.name == "h1":
                found_h1 = True
                break
            else:
                element.extract()
        if not found_h1:
            raise ValueError(f"Malformed HTML: no main title (h1 tag)")
        return article

    @staticmethod
    def parse(raw_html: str) -> str:
        """
        Parses the raw HTML string representing the webpage and returns
        the article converted to markdown

        :param raw_html:
        :return: markdown with only the relevant content
        """
        html = BeautifulSoup(raw_html, 'html.parser')
        article = CPAlgoParser.get_base_content(html)
        article = CPAlgoParser.remove_headers_until_first_h1(article)
        article = CodeBlockFormatter.format_all_blocks(article)
        with open("data/dbg_html", "w") as dump_file:
            print(article, file=dump_file)
        return CPAlgoParser.to_markdown(article)

    @staticmethod
    def parse_navigation_page(raw_html: str) -> list[tuple[str, str]]:
        """
        From the raw HTML content of the navigation page, return the list of URLs
        with the links for the articles/pages and the descriptions
        """
        BASE_URL = "https://cp-algorithms.com"
        links = []
        html = BeautifulSoup(raw_html, 'html.parser')
        for tag in html.descendants:
            if isinstance(tag, Tag):
                if (
                    tag.name == "a"
                    and tag.has_attr("href")
                    and tag.has_attr("class")
                    and "md-nav__link" in tag.attrs["class"]
                    and "/" in tag.attrs["href"]  # links in top-level are not articles
                    # article links are like <category>/<page_name>.html
                ):
                    link = "/".join([BASE_URL, tag.attrs["href"]])
                    description = None
                    # Get the first child <span class="md-ellipsis"> inside the current <a> tag
                    span = tag.find("span", class_="md-ellipsis")
                    if span:
                        description = span.get_text().strip()
                    links.append((link, description))
        return links


if __name__ == "__main__":
    fpath = sys.argv[1]
    with open(fpath, 'r') as f:
        raw_content = f.read()
    print(CPAlgoParser.parse(raw_content))
