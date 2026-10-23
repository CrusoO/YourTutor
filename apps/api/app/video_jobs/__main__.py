from app.db.session import session_factory
from app.video_jobs.worker import main_loop

main_loop(session_factory())
