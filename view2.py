import curses
import requests
import argparse
from datetime import datetime

class GitHubViewer:
    def __init__(self, username):
        self.username = username
        self.repos = []
        self.commits = []
        self.file_changes = []
        self.current_pane = 0
        self.selected_repo = None
        self.selected_commit = None
        self.selected_file = None
        self.file_content = []

    def fetch_repos(self):
        url = f"https://api.github.com/users/{self.username}/repos"
        response = requests.get(url)
        if response.status_code == 200:
            self.repos = response.json()
        else:
            self.repos = []

    def fetch_commits(self):
        if not self.selected_repo:
            return
        url = f"https://api.github.com/repos/{self.username}/{self.selected_repo['name']}/commits"
        response = requests.get(url)
        if response.status_code == 200:
            self.commits = response.json()
        else:
            self.commits = []

    def fetch_file_changes(self):
        if not self.selected_commit:
            return
        url = f"https://api.github.com/repos/{self.username}/{self.selected_repo['name']}/commits/{self.selected_commit['sha']}"
        response = requests.get(url)
        if response.status_code == 200:
            self.file_changes = response.json()['files']
        else:
            self.file_changes = []

    def fetch_file_content(self):
        if not self.selected_file:
            return
        self.file_content = self.selected_file['patch'].split('\n') if 'patch' in self.selected_file else []

    def draw_pane(self, win, title, items, selected_index, start_col, width):
        win.addstr(0, start_col, title.center(width), curses.A_REVERSE)
        for i, item in enumerate(items[self.scroll_offsets[self.current_pane]:], start=1):
            if i > self.max_lines - 2:
                break
            if i - 1 + self.scroll_offsets[self.current_pane] == selected_index:
                win.addstr(i, start_col, item[:width].ljust(width), curses.A_REVERSE)
            else:
                win.addstr(i, start_col, item[:width].ljust(width))

    def run(self, stdscr):
        curses.curs_set(0)
        self.stdscr = stdscr
        self.max_y, self.max_x = self.stdscr.getmaxyx()
        self.max_lines = self.max_y - 1
        self.fetch_repos()

        self.selected_indices = [0, 0, 0, 0]
        self.scroll_offsets = [0, 0, 0, 0]

        while True:
            self.stdscr.clear()
            pane_width = self.max_x // 4

            # Draw repository pane
            repo_items = [repo['name'] for repo in self.repos]
            self.draw_pane(self.stdscr, "Repositories", repo_items, self.selected_indices[0], 0, pane_width)

            # Draw commit pane
            commit_items = [f"{commit['sha'][:7]} - {commit['commit']['message'].split()[0]}" for commit in self.commits]
            self.draw_pane(self.stdscr, "Commits", commit_items, self.selected_indices[1], pane_width, pane_width)

            # Draw file changes pane
            file_items = [f"{file['filename']} ({file['status']})" for file in self.file_changes]
            self.draw_pane(self.stdscr, "File Changes", file_items, self.selected_indices[2], pane_width * 2, pane_width)

            # Draw file content pane
            self.draw_pane(self.stdscr, "File Content", self.file_content, self.selected_indices[3], pane_width * 3, pane_width)

            self.stdscr.refresh()

            key = self.stdscr.getch()
            if key == ord('q'):
                break
            elif key == ord('h') and self.current_pane > 0:
                self.current_pane -= 1
            elif key == ord('l') and self.current_pane < 3:
                self.current_pane += 1
            elif key == ord('j'):
                self.selected_indices[self.current_pane] += 1
                max_index = len(self.repos) - 1 if self.current_pane == 0 else \
                            len(self.commits) - 1 if self.current_pane == 1 else \
                            len(self.file_changes) - 1 if self.current_pane == 2 else \
                            len(self.file_content) - 1
                self.selected_indices[self.current_pane] = min(self.selected_indices[self.current_pane], max_index)
                if self.selected_indices[self.current_pane] - self.scroll_offsets[self.current_pane] > self.max_lines - 3:
                    self.scroll_offsets[self.current_pane] += 1
            elif key == ord('k'):
                self.selected_indices[self.current_pane] -= 1
                self.selected_indices[self.current_pane] = max(self.selected_indices[self.current_pane], 0)
                if self.selected_indices[self.current_pane] < self.scroll_offsets[self.current_pane]:
                    self.scroll_offsets[self.current_pane] -= 1
            elif key == ord('\n'):  # Enter key
                if self.current_pane == 0 and self.repos:
                    self.selected_repo = self.repos[self.selected_indices[0]]
                    self.fetch_commits()
                    self.selected_indices[1] = 0
                    self.scroll_offsets[1] = 0
                    self.current_pane = 1
                elif self.current_pane == 1 and self.commits:
                    self.selected_commit = self.commits[self.selected_indices[1]]
                    self.fetch_file_changes()
                    self.selected_indices[2] = 0
                    self.scroll_offsets[2] = 0
                    self.current_pane = 2
                elif self.current_pane == 2 and self.file_changes:
                    self.selected_file = self.file_changes[self.selected_indices[2]]
                    self.fetch_file_content()
                    self.selected_indices[3] = 0
                    self.scroll_offsets[3] = 0
                    self.current_pane = 3

def main(username):
    viewer = GitHubViewer(username)
    curses.wrapper(viewer.run)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="View GitHub repository commit logs and file changes.")
    parser.add_argument("username", help="GitHub username")
    args = parser.parse_args()
    main(args.username)

print("GitHub repository viewer (Ranger-like) script with detailed file changes created successfully. You can now run it with a GitHub username as an argument.")

