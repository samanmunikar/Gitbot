#import argparse
import datetime
import logging
import sys
import os
import subprocess
import time

# To make python 2 and 3 compatible
try:
    import configparser # python 3
except ImportError:
    import ConfigParser as configparser   # python 2

# To make python 2 and 3 compatible
try:
    from urllib.parse import urlparse  # python 3
except ImportError:
    from urlparse import urlparse   # python 2

# To make python 2 and 3 compatible
try:
    from urllib.parse import quote # python 3
except ImportError:
    from urllib import quote    # python 2

def cmd(*args, **kwargs):
    """
    Execute terminal commands using subprocess.
    :param args: terminal commands with each word as an element of a list
    :param kwargs: Keyworded arguments to specify some options
    :return: Output of terminal command
    """
    return subprocess.check_output(*args, **kwargs).decode().strip()


def get_repo_and_branch_from(dest):
    """
    Get Repository URL and branch name in the destination folder
    :param dest: location of the repository
    :return: Remote repository URL and branch name, both in lower case
    """
    if not os.path.exists(os.path.join(dest, '.git')):
        logging.error("Repository not found in {}".format(dest))
        raise ValueError("Repository not found in {}".format(dest))

    remote = cmd('git config --get remote.origin.url'.split(), cwd=dest)
    branch = cmd('git rev-parse --abbrev-ref HEAD'.split(), cwd=dest)

    return remote.lower(), branch.lower()


def build_repo(repo, dest, branch):
    """
    If repository repo is not available at the dest location, clone the repository of the given branch
    else if the repository is already available at the dest folder, check whether it is the same repository
    as remote repo and check if it has uncommitted changes.
    :param repo: Remote repository URL
    :param dest: Destination Location of local repository
    :param branch: Branch name of remote repository
    :return: None
    """
    dest = os.path.expanduser(dest)
    repo_name = urlparse(repo).path

    if not os.path.exists(os.path.join(dest, '.git')):
        result = cmd(['git', 'clone', '--no-checkout', '-b', branch, repo, dest], cwd=dest)
        logging.info('Cloned ...{repo_name}'.format(**locals()))
    else:
        current_remote, current_branch = get_repo_and_branch_from(dest)
        repo = repo.lower()
        branch = branch.lower()
        if not repo.endswith('.git'):
            repo += '.git'
        if not current_remote.endswith('.git'):
            current_remote += '.git'
        parsed_remote = urlparse(current_remote)
        parsed_repo = urlparse(repo)

        if (parsed_remote.netloc.split("@")[-1] != parsed_repo.netloc.split("@")[-1]
            or parsed_remote.path != parsed_repo.path):
            logging.error('Requested repo {} and destination cloned repo {} are different:'.format(repo_name,
                                                                                                   urlparse(
                                                                                                       current_remote).path))
            raise ValueError('Requested repo {} and destination cloned repo {} are different:'.format(repo_name,
                                                                                                      urlparse(
                                                                                                          current_remote).path))

        if branch != current_branch:
            logging.error('Requested branch {} and destination branch {} are different.'.format(branch, current_branch))
            raise ValueError(
                'Requested branch {} and destination branch {} are different.'.format(branch, current_branch))

        check_status = cmd('git status -s'.split(), cwd=dest)
        if check_status:
            logging.error('There are some uncommitted changes at {} that syncing would override'.format(dest))
            raise ValueError('There are some uncommitted changes at {} that syncing would override'.format(dest))


def synchronize_repo(repo, dest, branch):
    """
    Fetch changes from remote branch repository to local repository.
    :param repo: Remote repository URL
    :param dest: Destination Location of local repository
    :param branch: ranch name of remote repository
    :return: None
    """
    # pull changes in the branch
    result = cmd(['git', 'fetch', 'origin', branch], cwd=dest)
    logging.info('Fetched {branch}: {result}'.format(**locals()))

    # Hard reset the working directory 
    result = cmd(['git', 'reset', '--hard', 'origin/' + branch], cwd=dest)

    # Remove untracked files in the directory if any
    cmd(['git', 'clean', '-fdq'], cwd=dest)

    logging.info("Revision at : {}".format(cmd("git rev-parse HEAD".split(), cwd=dest)))
    logging.info("Reset to {}".format(result))
    logging.info("Finished syncing Repo {} at {}".format(urlparse(repo).path, datetime.datetime.now()))


def git_sync(repo, dest, branch, poll):
    """
    Synchronize our local repository of the given branch present in dest folder
    with the Remote repository with repo URL in every poll seconds.
    :param repo: Remote repository URL
    :param dest: Destination Location of local repository
    :param branch: Branch name of remote repository to sync
    :param poll: Time in seconds to trigger git synchronization
    :return: None
    """
    if not repo and not branch:
        repo, branch = get_repo_and_branch_from(dest)
    elif not repo:
        repo, _ = get_repo_and_branch_from(dest)
    elif not branch:
        branch = 'master'

    build_repo(repo, dest, branch)
    while True:
        synchronize_repo(repo, dest, branch)
        logging.info('polling {} seconds...'.format(poll))
        time.sleep(int(poll))


if __name__ == "__main__":
    # Take config file as the first parameter when calling this script
    #parser = argparse.ArgumentParser(description="#########  Welcome to GitBot  ###########")
    #parser.add_argument('configFile', metavar='config', type=str, help="Configuration File Name for GitBot")
    #args = parser.parse_args()
    #configFile = args.configFile
    configFile = str(sys.argv[1])

    # Read the content from config file
    config = configparser.ConfigParser()
    config.read(r'{}'.format(configFile))
    url = config.get('url', 'url')
    dest = config.get('path', 'destinationPath')
    poll = config.get('time', 'pollinterval')
    branch = config.get('branch', 'branch')
    username = config.get('bitbucket.org', 'username')
    password = config.get('bitbucket.org', 'password')
    enc_username = quote(username)
    enc_password = quote(password)
    repo = urlparse(url).scheme+"://"+enc_username+":"+enc_password+"@"+urlparse(url).netloc.split('@')[-1]+urlparse(url).path

    # Log all the synchronization activities
    logging.basicConfig(filename='gitbotlog_' + str(datetime.date.today()) + ".log",
                        format='%(asctime)s -  %(levelname)s - %(message)s',
                        level=logging.INFO)

    # Call Git Synchronization function
    git_sync(repo, dest, branch, poll)
