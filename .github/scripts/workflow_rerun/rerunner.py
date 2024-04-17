import sys
import tempfile
from pathlib import Path

from github import Github, Auth
from workflow_rerun.argument_parser import get_arguments
from workflow_rerun.constants import GITHUB_TOKEN, LOGGER
from workflow_rerun.log_analyzer import LogAnalyzer
from workflow_rerun.log_collector import collect_logs_for_run

if __name__ == '__main__':

    args = get_arguments()
    run_id = args.run_id
    repository_name = args.repository_name

    github = Github(auth=Auth.Token(token=GITHUB_TOKEN))
    gh_repo = github.get_repo(full_name_or_id=repository_name)
    run = gh_repo.get_workflow_run(id_=run_id)
    
    LOGGER.info(f'CHECKING IF RERUN IS NEEDED FOR {run.html_url} RUN IN {repository_name}.')
    
    # Check if the run has already been retriggered
    # we do not want to fall into a loop with retriggers
    if run.run_attempt > 1:
        LOGGER.info(f'THERE ARE {run.run_attempt} ATTEMPTS ALREADY. NOT CHECKING LOGS AND NOT RETRIGGERING. EXITING')
        sys.exit(0)
        
    log_archive_path = Path(tempfile.NamedTemporaryFile(suffix='.zip').name)

    collect_logs_for_run(
        run=run,
        log_archive_path=log_archive_path,
    )

    log_analyzer = LogAnalyzer(
        path_to_log_archive=log_archive_path,
        path_to_errors_file=args.error_to_look_for_file,
    )
    log_analyzer.analyze()
    
    if log_analyzer.found_matching_error:
        LOGGER.info(f'FOUND MATCHING ERROR, RETRIGGERING {run.html_url}')
        status = run.rerun()
        if status:
            LOGGER.info(f'RUN RETRIGGERED SUCCESSFULLY: {run.html_url}')
        else:
            LOGGER.info(f'RUN WAS NOT RETRIGGERED, SEE ABOVE')
        
        # "status" is True (which is 1) if everything is ok, False (which is 0) otherwise
        sys.exit(not status)
    else:
        LOGGER.info(f'NO ERROR WAS FOUND, NOT RETRIGGERING')
