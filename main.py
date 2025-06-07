from movies_data_push import create_and_categorize_movies, movies_tmdb, push_movies
from series_data_push import push_episodes, series_tmdb, create_and_categorize_series, push_series
from settings import BASE_URL, SERVER_ID, BASE_DIR
from movies_data_gen import diff_movies, gen_movies
from series_data_gen import diff_series, gen_episodes, gen_series, diff_episodes
from utils import login





# Main logic
session = login(BASE_URL)
if session:

    print(" copyrights reserved, you don't have the permission to own , share or sell the source code without the developer consent ")
    #gen_movies(f"{BASE_DIR}/movies")
    #diff_movies(session, BASE_URL, "movies.json")
    #push_movies(session, SERVER_ID, BASE_URL)
    #movies_tmdb(session, SERVER_ID, BASE_URL)
    create_and_categorize_movies(session, SERVER_ID, BASE_URL)
    #gen_series(f"{BASE_DIR}/seasons")
    #diff_series(session, BASE_URL, "series.json")
    #push_series(session, BASE_URL)
    #series_tmdb(session, BASE_URL)
    create_and_categorize_series(session,SERVER_ID, BASE_URL)
    #gen_episodes(f"{BASE_DIR}/seasons")
    #diff_episodes(session, BASE_URL, "episodes.json")
    #push_episodes(session, BASE_URL)



