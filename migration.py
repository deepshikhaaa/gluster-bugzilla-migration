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
GH_REPO = "gluster/glusterfs"
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

def close_bug(issue, bug):
    closing_msg = "This bug is moved to %s, and will be tracked there from now on. Visit GitHub issues URL for further details" % issue.html_url

    # TODO: uncomment it in last stage
    bug.close('UPSTREAM', comment=closing_msg)


def migrate_bug(gh, bzapi, users, bugId):
    bug = bzapi.getbug(bugId)
    if bug.status == "CLOSED":
        print("Bug %d is CLOSED, not migrating" % bugId)
        return

    if bug.component == 'project-infrastructure':
        GH_REPO = 'gluster/project-infrastructure'
    else:
        GH_REPO = 'gluster/glusterfs'

    repo = gh.get_repo(GH_REPO)
    email = "%s" % bug.assigned_to_detail["email"]
    assignee = users.get(email, None)
    summary = "[bug:%d] %s" % (bugId, bug.summary)

    comments = bug.getcomments()
    body = "URL: %s/%s\nCreator: %s\nTime: %s\n\n%s" % (
        BZ_URL, bugId,
        replace_email(comments[0]['creator']),
        comments[0]['time'],
        comments[0]['text']
    )

    # set the priority labels
    if bug.priority == 'low':
        GH_LABELS = ["Migrated", "Type:Bug", "Prio: Low"]
    if bug.priority == 'medium':
        GH_LABELS = ["Migrated", "Type:Bug", "Prio: Medium"]
    if bug.priority == 'high':
        GH_LABELS = ["Migrated", "Type:Bug", "Prio: High"]
    if bug.priority == 'urgent':
        GH_LABELS = ["Migrated", "Type:Bug", "Prio: Urgent"]
    else:
        GH_LABELS = ["Migrated", "Type:Bug"]

    issue = create_issue(repo, summary, body,
                         GH_LABELS, assignee)

    for obj in comments[1:]:
        comment =  "Time: %s\n%s commented: \n%s" % (
            obj['time'], replace_email(obj['creator']), obj['text']
        )
        issue.create_comment(comment)

    # Comment it in testing
    close_bug(issue, bug)
    print("Bug %d is now migrated to %s" % (bugId, issue.url))


def replace_email(detail):
    rep={'@': ' at ', '.com': ''}
    for x,y in rep.items():
        detail = detail.replace(x, y)
    return detail


def main():
    # using username and password
    gh = Github(GH_USER, GH_PASS)

    user_dict = setup()

    #gh = Github(GH_TOKEN)
    #repo = gh.get_repo(GH_REPO)
    bzapi = bugzilla.Bugzilla(BZ_URL)

    if not bzapi.logged_in:
        print("requires login credentials for %s, as we are closing bugs in this script" % BZ_URL)
        bzapi.interactive_login()
    # for each bug in the file:
    with open("bug.list") as bzlist:
        bugId = bzlist.readline()
        while bugId:
            try:
                migrate_bug(gh, bzapi, user_dict, int(bugId))
            except:
                pass
            bugId = bzlist.readline()

main()
