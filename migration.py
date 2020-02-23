import os
import json
import pprint
import bugzilla

from github import Github

# public test instance of bugzilla.redhat.com. It's okay to make changes
BZ_URL = "https://bugzilla.redhat.com"

# First create a Github instance:

GH_USER = ""
GH_PASS = ""
GH_TOKEN = ""
GH_REPO = "amarts/glusterfs"
GH_LABELS = ["Migrated", "Type:Bug"]

def create_issue(repo_handle, title, desc, labels, assign=None):
    if not assign:
        return repo_handle.create_issue(title=title,
                                        body=desc,
                                        labels=labels)
    who = []
    who.append(assign)
    return  repo_handle.create_issue(title=title,
                                     body=desc,
                                     labels=labels,
                                     assignees=who)

def setup():
    bz_to_gh_map = {}
    with open("assignee.list") as alist:
        line = alist.readline()
        while line:
            email, gh_id = line.split(' ')
            bz_to_gh_map[email] = gh_id.strip()
            line = alist.readline()

    return bz_to_gh_map

def close_bug(issue, bug, bzapi, bugId):
    closing_msg = "This bug is moved to %s, and will be tracked there from now on. Visit GitHub issues URL for further details" % issue.url

    # TODO: uncomment it in last stage
    bug.close('UPSTREAM', comment=closing_msg)


def migrate_bug(ghrepo, bzapi, users, bugId):
    bug = bzapi.getbug(bugId)
    email = "%s@redhat.com" % bug.assigned_to_detail["email"]
    #assignee = users.get(email, None)
    assignee = "amarts"
    summary = "[bug:%d] %s" % (bugId, bug.summary)

    comments = bug.getcomments()
    body = "bugzilla-URL: %s/%s\n%s" % (BZ_URL, bugId, comments[0]['text'])
    issue = create_issue(ghrepo, summary, body,
                         GH_LABELS, assignee)

    # Update only the latest message in the github issue,
    # and allow it to be lightweight to start with.
    comment = None
    if len(comments) > 2:
        obj = comments[-1]
        comment = "Creator: %s\nTime: %s\nText: %s" % (
            obj['creator'], obj['time'], obj['text']
        )
    if comment:
        issue.create_comment(comment)

    # Comment it in testing
    close_bug(issue, bug, bzapi, bugId)
    print("Bug %d is now migrated to %s" % (bugId, issue.url))

def main():
    # using username and password
    # gh = Github(GH_USER, GH_PASS)

    user_dict = setup()

    gh = Github(GH_TOKEN)
    repo = gh.get_repo(GH_REPO)
    bzapi = bugzilla.Bugzilla(BZ_URL)

    if not bzapi.logged_in:
        print("requires login credentials for %s, as we are closing bugs in this script" % BZ_URL)
        bzapi.interactive_login()

    # for each bug in the file:
    with open("bug.list") as bzlist:
        bugId = bzlist.readline()
        while bugId:
            migrate_bug(repo, bzapi, user_dict, int(bugId))
            bugId = bzlist.readline()

main()
