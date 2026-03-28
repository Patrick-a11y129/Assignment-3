"""
AI Movie Recommendation System
Streamlit App version
"""

import streamlit as st
from datetime import datetime
from typing import List, Dict, Tuple, Optional
import json
import os

# ============================================
# CONFIGURATION
# ============================================

DATA_FILE = "mrs_data.json"

# ============================================
# CLASSES FROM PART C (Preserved)
# ============================================

class Movie:
    def __init__(self, movie_id: str, title: str, genre: List[str],
                 release_year: int, duration: int, description: str = ""):
        self.movie_id = movie_id
        self.title = title
        self.genre = genre
        self.release_year = release_year
        self.duration = duration
        self.description = description

        self.rating_sum = 0.0
        self.rating_count = 0
        self.view_count = 0
        self.all_ratings: List[float] = []

    @property
    def average_rating(self) -> float:
        if self.rating_count == 0:
            return 0.0
        return self.rating_sum / self.rating_count

    def update_rating(self, new_rating: float) -> None:
        self.rating_sum += new_rating
        self.rating_count += 1
        self.all_ratings.append(new_rating)

    def increment_view_count(self) -> None:
        self.view_count += 1

    def genre_match_score(self, user_genres: List[str]) -> int:
        return sum(1 for g in self.genre if g in user_genres)

    def get_trending_score(self) -> float:
        rating_component = self.average_rating * 0.7
        view_component = min(self.view_count / 100, 5.0) * 0.3
        return rating_component + view_component

    def to_dict(self) -> dict:
        return {
            'movie_id': self.movie_id,
            'title': self.title,
            'genre': self.genre,
            'release_year': self.release_year,
            'duration': self.duration,
            'description': self.description,
            'rating_sum': self.rating_sum,
            'rating_count': self.rating_count,
            'view_count': self.view_count
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Movie':
        movie = cls(
            data['movie_id'],
            data['title'],
            data['genre'],
            data['release_year'],
            data['duration'],
            data.get('description', '')
        )
        movie.rating_sum = data.get('rating_sum', 0)
        movie.rating_count = data.get('rating_count', 0)
        movie.view_count = data.get('view_count', 0)
        return movie


class User:
    def __init__(self, user_id: str, name: str, email: str, age: int, password: str = ""):
        self.user_id = user_id
        self.name = name
        self.email = email
        self.age = age
        self.password = password

        self.favorite_genres: List[str] = []
        self.viewing_history: List[Tuple[Movie, str, int]] = []
        self.ratings: Dict[str, float] = {}

    def add_favorite_genres(self, genres: List[str]) -> None:
        self.favorite_genres = genres

    def rate_movie(self, movie: Movie, rating: float) -> None:
        self.ratings[movie.movie_id] = rating
        movie.update_rating(rating)

    def watch_movie(self, movie: Movie, minutes_watched: Optional[int] = None) -> None:
        if minutes_watched is None:
            minutes_watched = movie.duration
        today = datetime.now().strftime("%Y-%m-%d")
        self.viewing_history.append((movie, today, minutes_watched))
        movie.increment_view_count()

    def get_total_watch_count(self) -> int:
        return len(self.viewing_history)

    def get_total_watch_time(self) -> int:
        return sum(minutes for movie, date, minutes in self.viewing_history)

    def to_dict(self) -> dict:
        return {
            'user_id': self.user_id,
            'name': self.name,
            'email': self.email,
            'age': self.age,
            'password': self.password,
            'favorite_genres': self.favorite_genres,
            'ratings': self.ratings,
            'viewing_history': [
                {'movie_id': m.movie_id, 'date': d, 'minutes': mins}
                for m, d, mins in self.viewing_history
            ]
        }

    @classmethod
    def from_dict(cls, data: dict, engine: 'RecommendationEngine') -> 'User':
        user = cls(
            data['user_id'],
            data['name'],
            data['email'],
            data['age'],
            data.get('password', '')
        )
        user.favorite_genres = data.get('favorite_genres', [])
        user.ratings = data.get('ratings', {})

        for h in data.get('viewing_history', []):
            movie = engine.get_movie_by_id(h['movie_id'])
            if movie:
                user.viewing_history.append((movie, h['date'], h['minutes']))

        return user


class RecommendationEngine:
    def __init__(self):
        self.all_movies: Dict[str, Movie] = {}
        self.all_users: Dict[str, User] = {}
        self.current_user: Optional[User] = None

    def add_movie(self, movie: Movie) -> None:
        self.all_movies[movie.movie_id] = movie

    def get_movie_by_id(self, movie_id: str) -> Optional[Movie]:
        return self.all_movies.get(movie_id)

    def register_user(self, user: User) -> bool:
        if user.user_id in self.all_users:
            return False
        self.all_users[user.user_id] = user
        return True

    def login_user(self, user_id: str, password: str) -> Optional[User]:
        user = self.all_users.get(user_id)
        if user and user.password == password:
            self.current_user = user
            return user
        return None

    def recommend_by_genre(self, user: User, top_n: int = 5) -> List[Movie]:
        if not user.favorite_genres:
            return []

        scored_movies = []
        for movie in self.all_movies.values():
            if movie.movie_id in user.ratings:
                continue

            match_score = movie.genre_match_score(user.favorite_genres)
            if match_score > 0:
                scored_movies.append((match_score, movie.average_rating, movie))

        scored_movies.sort(reverse=True, key=lambda x: (x[0], x[1]))
        return [movie for score, rating, movie in scored_movies[:top_n]]

    def recommend_by_rating(self, user: User, top_n: int = 5) -> List[Movie]:
        unrated = [m for m in self.all_movies.values()
                   if m.movie_id not in user.ratings]
        unrated.sort(key=lambda m: m.average_rating, reverse=True)
        return unrated[:top_n]

    def generate_recommendations(self, user: User, top_n: int = 5) -> List[Movie]:
        genre_recs = self.recommend_by_genre(user, top_n)
        rating_recs = self.recommend_by_rating(user, top_n)

        combined = []
        seen = set()

        for movie in genre_recs + rating_recs:
            if movie.movie_id not in seen and len(combined) < top_n:
                combined.append(movie)
                seen.add(movie.movie_id)

        return combined

    def search_by_title(self, keyword: str) -> List[Movie]:
        keyword = keyword.lower()
        return [m for m in self.all_movies.values()
                if keyword in m.title.lower()]

    def search_by_genre(self, genre: str) -> List[Movie]:
        genre = genre.title()
        return [m for m in self.all_movies.values()
                if genre in [g.title() for g in m.genre]]

    def search_by_year(self, year: int) -> List[Movie]:
        return [m for m in self.all_movies.values()
                if m.release_year == year]

    def get_most_popular_genre(self) -> List[Tuple[str, int]]:
        genre_views: Dict[str, int] = {}
        for movie in self.all_movies.values():
            for genre in movie.genre:
                genre_views[genre] = genre_views.get(genre, 0) + movie.view_count
        return sorted(genre_views.items(), key=lambda x: x[1], reverse=True)

    def get_trending_movies(self, top_n: int = 5) -> List[Movie]:
        return sorted(self.all_movies.values(),
                      key=lambda m: m.get_trending_score(),
                      reverse=True)[:top_n]

    def get_most_watched_movies(self, top_n: int = 5) -> List[Movie]:
        return sorted(self.all_movies.values(),
                      key=lambda m: m.view_count,
                      reverse=True)[:top_n]

    def get_top_rated_movies(self, top_n: int = 5) -> List[Movie]:
        return sorted(self.all_movies.values(),
                      key=lambda m: m.average_rating,
                      reverse=True)[:top_n]

    def get_most_active_users(self, top_n: int = 5) -> List[Tuple[User, int]]:
        user_activity = [(u, u.get_total_watch_count()) for u in self.all_users.values()]
        user_activity.sort(key=lambda x: x[1], reverse=True)
        return user_activity[:top_n]

# ============================================
# Persistent data(save to json)
# ============================================

def save_data(engine: RecommendationEngine) -> bool:
    try:
        data = {
            'movies': [m.to_dict() for m in engine.all_movies.values()],
            'users': [u.to_dict() for u in engine.all_users.values()]
        }
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        st.error(f"Error saving data: {e}")
        return False


def load_data(engine: RecommendationEngine) -> bool:
    if not os.path.exists(DATA_FILE):
        return False

    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)

        engine.all_movies.clear()
        engine.all_users.clear()

        for m_data in data.get('movies', []):
            movie = Movie.from_dict(m_data)
            engine.add_movie(movie)

        for u_data in data.get('users', []):
            user = User.from_dict(u_data, engine)
            engine.register_user(user)

        return True
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return False

def add_demo_data(engine: RecommendationEngine):
    #Inbuilt movies and users for demo
    movies = [
        Movie("M1", "Inception", ["Sci-Fi", "Action", "Thriller"], 2010, 148,
              "A thief who steals corporate secrets through dreams"),
        Movie("M2", "The Dark Knight", ["Action", "Crime", "Drama"], 2008, 152,
              "Batman faces the Joker"),
        Movie("M3", "Interstellar", ["Sci-Fi", "Adventure", "Drama"], 2014, 169,
              "A team travels through a wormhole"),
        Movie("M4", "Pulp Fiction", ["Crime", "Drama"], 1994, 154,
              "Lives of two mob hitmen intertwine"),
        Movie("M5", "The Matrix", ["Sci-Fi", "Action"], 1999, 136,
              "A desk job worker awakens to find society trapped in a virtual world"),
        Movie("M6", "Parasite", ["Thriller", "Drama", "Comedy"], 2019, 132,
              "A poor family schemes into a wealthy household"),
        Movie("M7", "The Godfather", ["Crime", "Drama"], 1972, 175,
              "The aging patriarch of an organized crime dynasty"),
        Movie("M8", "Forrest Gump", ["Drama", "Comedy", "Romance"], 1994, 142,
              "The story of a simple man with low IQ who lives through important time periods in America"),
        Movie("M9","The Bone Collector",["Thriller","Crime","Horror"],1999,118,
              "A detective and her bedridden friend race to find a serial killer")
    ]

    for m in movies:
        engine.add_movie(m)

    patricia = User("U1", "Patricia", "patricia@email.com", 25, "pass")
    patricia.add_favorite_genres(["Sci-Fi", "Action"])
    patricia.watch_movie(movies[0])
    patricia.rate_movie(movies[0], 5.0)
    patricia.watch_movie(movies[2])
    patricia.rate_movie(movies[2], 4.5)
    patricia.watch_movie(movies[4])
    patricia.rate_movie(movies[4], 5.0)

    alex = User("U2", "Alex", "alex@email.com", 30, "pass")
    alex.add_favorite_genres(["Crime", "Drama"])
    alex.watch_movie(movies[1])
    alex.rate_movie(movies[1], 5.0)
    alex.watch_movie(movies[3])
    alex.rate_movie(movies[3], 4.5)
    alex.watch_movie(movies[6])
    alex.rate_movie(movies[6], 5.0)

    engine.register_user(patricia)
    engine.register_user(alex)
    save_data(engine)


# ============================================
# Visualize the analyzed data
# ============================================

def make_bar(value, max_value, width=20):
    """Create ASCII bar chart."""
    filled = int((value / max_value) * width) if max_value > 0 else 0
    return "█" * filled + "░" * (width - filled)


def make_stars(rating):
    """Create star rating display."""
    full = int(rating)
    half = 1 if rating - full >= 0.5 else 0
    empty = 5 - full - half
    return " :star: " * full + ("½" if half else "") + "☆" * empty


def color_rating(rating):
    """Return color based on rating."""
    if rating >= 4.5:
        return ":large_green_circle:"
    elif rating >= 3.5:
        return ":large_yellow_circle:"
    elif rating >= 2.5:
        return ":large_orange_circle:"
    else:
        return ":large_red_circle:"


def get_medal(rank):
    """Return medal emoji for rank."""
    medals = {1: ":1st_place_medal:", 2: ":2nd_place_medal:", 3: ":3rd_place_medal:"}
    return medals.get(rank, f"{rank}.")


# ============================================
# Initialize
# ============================================

def init_engine():
    if 'engine' not in st.session_state:
        engine = RecommendationEngine()

        if not load_data(engine):
            add_demo_data(engine)
            st.info("Created demo data (no previous save found)")

        st.session_state.engine = engine
        st.session_state.admin_logged_in = False
        st.session_state.data_modified = False


init_engine()
engine = st.session_state.engine

st.set_page_config(page_title="Movie Rec System", layout="wide")
st.title(" AI Movie Recommendation System")

# Sidebar
st.sidebar.header("Navigation")

st.sidebar.markdown("---")
st.sidebar.subheader(" :floppy_disk: Data")
if st.sidebar.button("Save Now"):
    if save_data(engine):
        st.sidebar.success("Saved!")
        st.session_state.data_modified = False

if st.sidebar.button("Reset to Demo"):
    if os.path.exists(DATA_FILE):
        os.remove(DATA_FILE)
    st.session_state.clear()
    st.rerun()

if st.session_state.get('data_modified'):
    st.sidebar.caption(" :warning: Unsaved changes")

st.sidebar.markdown("---")

all_genres = list(set(g for m in engine.all_movies.values() for g in m.genre))
page = st.sidebar.radio("Go to", ["Home", "Search", "Recommendations", "Dashboard(and Login)", "Admin"])

if engine.current_user:
    st.sidebar.success(f"Logged in: {engine.current_user.name}")
    if st.sidebar.button("Logout"):
        engine.current_user = None
        st.rerun()
else:
    st.sidebar.info("Not logged in")

# ============================================
# Home Page
# ============================================

if page == "Home":
    st.header("Browse & Rate Movies")

    movies = list(engine.all_movies.values())

    col1, col2 = st.columns(2)
    with col1:
        filter_genre = st.selectbox("Filter by genre", ["All"] + all_genres)
    with col2:
        sort_by = st.selectbox("Sort by", ["Rating", "Views", "Year"])

    if filter_genre != "All":
        movies = [m for m in movies if filter_genre in m.genre]

    if sort_by == "Rating":
        movies.sort(key=lambda m: m.average_rating, reverse=True)
    elif sort_by == "Views":
        movies.sort(key=lambda m: m.view_count, reverse=True)
    else:
        movies.sort(key=lambda m: m.release_year, reverse=True)

    for movie in movies:
        with st.container(border=True):
            col1, col2, col3 = st.columns([3, 2, 1])

            with col1:
                st.subheader(movie.title)
                st.caption(f"{movie.release_year} | {', '.join(movie.genre)} | {movie.duration} min")
                st.write(movie.description)
                stars = make_stars(movie.average_rating)
                st.write(f"{color_rating(movie.average_rating)} {stars} {movie.average_rating:.1f}/5")
                st.caption(f"({movie.rating_count} ratings) | 👁️ {movie.view_count} views")

            with col2:
                if engine.current_user:
                    if movie.movie_id in engine.current_user.ratings:
                        current = engine.current_user.ratings[movie.movie_id]
                        st.success(f"✓ You rated: {make_stars(current)} {current}/5")
                    else:
                        rating = st.slider(f"Rate", 1.0, 5.0, 3.0, 0.5,
                                           key=f"rate_{movie.movie_id}")
                        if st.button("Submit Rating", key=f"btn_{movie.movie_id}"):
                            engine.current_user.watch_movie(movie)
                            engine.current_user.rate_movie(movie, rating)
                            save_data(engine)
                            st.success(f"Rated {rating}/5!")
                            st.rerun()
                else:
                    st.info("Login to rate")

            with col3:
                with st.expander("Details"):
                    st.write(f"ID: {movie.movie_id}")
                    st.write(f"Trend Score: {movie.get_trending_score():.1f}")



# ============================================
# Search Page
# ============================================

elif page == "Search":
    st.header("🔍 Search Movies")

    st.subheader("Search by Multiple Criteria")
    col1, col2, col3 = st.columns(3)

    with col1:
        title_kw = st.text_input("Title keyword")
    with col2:
        search_genre = st.selectbox("Genre", [""] + all_genres)
    with col3:
        year_option = st.selectbox("Year filter", ["Any year", "Specific year"])
        if year_option == "Specific year":
            search_year = st.number_input("Enter year", 1900, 2030, 2020)
        else:
            search_year = None

    if st.button("Search"):
        results = list(engine.all_movies.values())

        if title_kw:
            results = [m for m in results if title_kw.lower() in m.title.lower()]
        if search_genre:
            results = [m for m in results if search_genre in m.genre]
        if search_year:
            results = [m for m in results if m.release_year == search_year]

        st.session_state.search_results = results
        st.rerun()

    # Display results clearly (Part a-IV) with Watch & Rate buttons
    if 'search_results' in st.session_state:
        results = st.session_state.search_results
        st.write(f"Found {len(results)} movie(s)")

        if results:
            # Table display
            data = []
            for m in results:
                data.append({
                    "Title": m.title,
                    "Genre": ", ".join(m.genre),
                    "Year": m.release_year,
                    "Average Rating": f"{m.average_rating:.1f}/5",
                    "Views": m.view_count
                })
            st.table(data)

            # Detailed view with Watch & Rate buttons -
            st.subheader(" Movie Details & Actions")
            for i, movie in enumerate(results):
                with st.expander(f"{movie.title} ({movie.release_year}) - Click to Watch/Rate"):
                    col1, col2 = st.columns([2, 1])

                    with col1:
                        st.write(f"**Description:** {movie.description}")
                        st.write(f"**Duration:** {movie.duration} minutes")
                        st.write(f"**Genres:** {', '.join(movie.genre)}")
                        st.write(f"**Average Rating:** {make_stars(movie.average_rating)} {movie.average_rating:.2f}/5")
                        st.write(f"**Total Views:** {movie.view_count}")

                    with col2:
                        # SAME AS RECOMMENDATIONS PAGE
                        if engine.current_user:
                            # Check if already viewed (same logic as recommendations)
                            viewed = any(h[0].movie_id == movie.movie_id for h in engine.current_user.viewing_history)

                            if viewed:
                                # Already viewed - show rating option or rated status
                                if movie.movie_id in engine.current_user.ratings:
                                    current = engine.current_user.ratings[movie.movie_id]
                                    st.success(f"✓ Rated: {make_stars(current)} {current}/5")
                                else:
                                    st.info("Watched! Rate now?")
                                    rating = st.slider("Rate", 1.0, 5.0, 3.0, 0.5,
                                                       key=f"search_rate_{movie.movie_id}_{i}")
                                    if st.button("Submit Rating", key=f"search_submit_{movie.movie_id}_{i}"):
                                        engine.current_user.rate_movie(movie, rating)
                                        save_data(engine)
                                        st.success(f"Rated {rating}/5! Saved.")
                                        st.rerun()
                            else:
                                # Not viewed yet - show View button (same as recommendations)
                                if st.button(":eyes: View Movie", key=f"search_view_{movie.movie_id}_{i}"):
                                    # Mark as viewed
                                    engine.current_user.watch_movie(movie)
                                    save_data(engine)
                                    st.success(f"Viewed! Now rate it?")
                                    st.rerun()
                        else:
                            st.info("Login to view and rate")
                            if st.button("Go to Login", key=f"search_login_{i}"):
                                st.session_state.page = "Dashboard"
                                st.rerun()


# ============================================
# PAGE: RECOMMENDATIONS
# ============================================

elif page == "Recommendations":
    st.header(" Top-N Recommendations")

    user = engine.current_user

    if not user:
        st.info("Please login to get personalized recommendations")
        st.stop()
    else:
        st.write(f"For: **{user.name}** | Genres: {', '.join(user.favorite_genres)}")
        n = st.slider("How many recommendations?", 1, 10, 5)

    recs = engine.generate_recommendations(user, n)

    if recs:
        st.subheader(f"Top-{n} Recommended for You")

        for i, movie in enumerate(recs, 1):
            with st.container(border=True):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"{get_medal(i)} **{movie.title}** ({movie.release_year})")
                    st.caption(f"{', '.join(movie.genre)}")
                    st.write(
                        f"{color_rating(movie.average_rating)} {make_stars(movie.average_rating)} {movie.average_rating:.1f}/5")
                    st.caption(f" {movie.view_count} views | Trend: {movie.get_trending_score():.1f}")

                with col2:
                    if engine.current_user:
                        # Check if already viewed
                        viewed = any(h[0].movie_id == movie.movie_id for h in engine.current_user.viewing_history)

                        if viewed:
                            # Already viewed - show rating option or rated status
                            if movie.movie_id in engine.current_user.ratings:
                                current = engine.current_user.ratings[movie.movie_id]
                                st.success(f"✓ Rated: {make_stars(current)} {current}/5")
                            else:
                                st.info("Watched! Rate now?")
                                rating = st.slider("Rate", 1.0, 5.0, 3.0, 0.5,
                                                   key=f"rate_viewed_{movie.movie_id}")
                                if st.button("Submit Rating", key=f"submit_viewed_{movie.movie_id}"):
                                    engine.current_user.rate_movie(movie, rating)
                                    save_data(engine)
                                    st.success(f"Rated {rating}/5! Saved.")
                                    st.rerun()
                        else:
                            # Not viewed yet - show View button
                            if st.button(" View Movie", key=f"view_{movie.movie_id}"):
                                # Mark as viewed
                                engine.current_user.watch_movie(movie)
                                save_data(engine)
                                st.success(f"Viewed! Now rate it?")
                                st.rerun()
                    else:
                        st.info("Login to view")
    else:
        st.warning("No recommendations found.")

# ============================================
# Dashboard(and Login) for Users
# ============================================


elif page == "Dashboard(and Login)":
    st.header("User Dashboard(and Login)")

    # Security: Login by email + password
    if not engine.current_user:
        st.subheader("Login")

        email = st.text_input("Email")
        password = st.text_input("Password", type="password")

        if st.button("Login"):
            # Find user by email (not showing list of users)
            user = next((u for u in engine.all_users.values()
                         if u.email == email and u.password == password), None)
            if user:
                engine.current_user = user
                st.success(f"Welcome back, {user.name}!")
                st.rerun()
            else:
                # Generic error message (don't reveal if email exists or not)
                st.error("Invalid email or password")

        # Registration
        with st.expander("New User? Register"):
            name = st.text_input("Full Name", key="reg_name")
            email_reg = st.text_input("Email", key="reg_email")
            age = st.number_input("Age", 13, 100, 25, key="reg_age")
            password_reg = st.text_input("Password", type="password", key="reg_pass")
            genres = st.multiselect("Favorite genres", all_genres, key="reg_genres")

            if st.button("Register"):
                # Check if email already exists
                if any(u.email == email_reg for u in engine.all_users.values()):
                    st.error("Email already registered. Please login.")
                else:
                    new_id = f"U{len(engine.all_users) + 1}"
                    new_user = User(new_id, name, email_reg, age, password_reg)
                    new_user.add_favorite_genres(genres)
                    engine.register_user(new_user)
                    engine.current_user = new_user
                    save_data(engine)
                    st.success(f"Account created! Welcome, {name}")
                    st.rerun()

        st.stop()

    user = engine.current_user
    # ... rest of dashboard code unchanged
    tab1, tab2, tab3 = st.tabs(["Overview", "History & Ratings", "Analytics"])

    # Tab 1: Overview
    with tab1:
        # Metrics with deltas
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Movies Watched", user.get_total_watch_count(),
                    delta=f"+{len([h for h in user.viewing_history if h[1] == datetime.now().strftime('%Y-%m-%d')])} today")
        col2.metric("Ratings Given", len(user.ratings))
        total_time = user.get_total_watch_time()
        col3.metric("Watch Time", f"{total_time // 60}h {total_time % 60}m")
        avg = sum(user.ratings.values()) / len(user.ratings) if user.ratings else 0
        col4.metric("Avg Rating Given", f"{avg:.1f}/5",
                    delta="Above avg" if avg > 3.5 else "Below avg")

        st.write(f"**Profile:** {user.name} | {user.email} | Genres: {', '.join(user.favorite_genres)}")

        # Top recommendations with medals
        st.subheader(" :trophy: Your Top Recommended Movies")
        recs = engine.generate_recommendations(user, 5)
        for i, m in enumerate(recs, 1):
            with st.container():
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"{get_medal(i)} **{m.title}** ({', '.join(m.genre)})")
                with col2:
                    st.write(f"{make_stars(m.average_rating)} {m.average_rating:.1f}★")

        # Trending movies
        st.subheader(" :fire: Trending Now")
        trending = engine.get_trending_movies(3)
        cols = st.columns(3)
        for i, (col, m) in enumerate(zip(cols, trending), 1):
            with col:
                with st.container(border=True):
                    st.write(f"{get_medal(i)}")
                    st.write(f"**{m.title}**")
                    st.caption(f"Trend Score: {m.get_trending_score():.1f}")
                    st.write(f"{make_stars(m.average_rating)}")

        # Popular genres with progress bars
        st.subheader(" :chart: Popular Genres")
        popular = engine.get_most_popular_genre()[:5]
        max_views = popular[0][1] if popular else 1
        for genre, views in popular:
            col1, col2, col3 = st.columns([2, 4, 1])
            with col1:
                st.write(f"**{genre}**")
            with col2:
                st.progress(views / max_views)
            with col3:
                st.caption(f"{views} views")

    # Tab 2: History & Ratings (Tabular)
    with tab2:
        col1, col2 = st.columns(2)

        with col1:
            st.write("** :star: Your Ratings**")
            if user.ratings:
                for mid, rating in sorted(user.ratings.items(), key=lambda x: x[1], reverse=True):
                    movie = engine.get_movie_by_id(mid)
                    if movie:
                        with st.container(border=True):
                            col_a, col_b = st.columns([3, 2])
                            with col_a:
                                st.write(f"**{movie.title}**")
                                st.caption(f"{', '.join(movie.genre[:2])}")
                            with col_b:
                                st.write(f"{make_stars(rating)} **{rating}/5**")
                                st.caption(f"Global: {movie.average_rating:.1f}★")
            else:
                st.info("No ratings yet")

        with col2:
            st.write("**Recent Watch History**")
            if user.viewing_history:
                for movie, date, mins in reversed(user.viewing_history[-5:]):
                    with st.container(border=True):
                        st.write(f"**{movie.title}**")
                        st.caption(f" {date} |  {mins} min")
                        st.write(f"{make_stars(movie.average_rating)} {movie.average_rating:.1f}★")
            else:
                st.info("No history yet")

    # Tab 3: Analytics - SIMPLIFIED VISUALIZATIONS
    with tab3:
        st.subheader(" :graph: Your Analytics")

        # Genre preferences with ASCII bars
        st.write("**Genre Preferences**")
        genre_counts: Dict[str, int] = {}
        for movie, date, mins in user.viewing_history:
            for g in movie.genre:
                genre_counts[g] = genre_counts.get(g, 0) + 1

        if genre_counts:
            max_count = max(genre_counts.values())
            sorted_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)

            for genre, count in sorted_genres:
                col1, col2, col3 = st.columns([2, 4, 1])
                with col1:
                    st.write(f"**{genre}**")
                with col2:
                    bar = make_bar(count, max_count, 25)
                    st.code(f"{bar}", language=None)
                with col3:
                    st.write(f"**{count}**")
        else:
            st.info("No viewing data")

        st.markdown("---")

        # Rating distribution with emoji bars
        st.write("** :starr: Your Rating Distribution**")
        if user.ratings:
            dist: Dict[int, int] = {}
            for r in user.ratings.values():
                dist[int(r)] = dist.get(int(r), 0) + 1

            max_dist = max(dist.values()) if dist else 1

            for rating in range(5, 0, -1):
                count = dist.get(rating, 0)
                col1, col2, col3 = st.columns([1, 4, 1])
                with col1:
                    st.write(f"**{rating}★**")
                with col2:
                    # Emoji bar
                    emoji_bar = " :star: " * count + "·" * (max_dist - count)
                    st.write(emoji_bar)
                with col3:
                    st.write(f"**{count}**")
        else:
            st.info("No ratings yet")

        st.markdown("---")

        # Your ratings vs Global with side-by-side comparison
        st.write("Your Ratings vs Global Average")
        if user.ratings:
            comparison_data = []
            for mid, rating in list(user.ratings.items())[:5]:
                movie = engine.get_movie_by_id(mid)
                if movie:
                    comparison_data.append((movie.title[:20], rating, movie.average_rating))

            for title, your_rating, global_rating in comparison_data:
                with st.container(border=True):
                    st.write(f"**{title}**")
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.write(f"You: {make_stars(your_rating)} **{your_rating}**")
                        st.progress(your_rating / 5.0)
                    with col_b:
                        st.write(f"Global: {make_stars(global_rating)} **{global_rating:.1f}**")
                        st.progress(global_rating / 5.0)


# ============================================
# Administration
# ============================================

elif page == "Admin":
    st.header(" Admin Console")

    if not st.session_state.admin_logged_in:
        key = st.text_input("Enter Admin Key", type="password")
        if st.button("Access"):
            if key == "1234":
                st.session_state.admin_logged_in = True
                st.success("Access granted!")
                st.rerun()
            else:
                st.error("Invalid key")
        st.stop()

    if st.button("Logout Admin"):
        st.session_state.admin_logged_in = False
        st.rerun()

    st.success("Administrator Mode")

    tab1, tab2 = st.tabs(["Movie Management", "Engagement Analytics"])

    with tab1:
        st.subheader("Movie Database Management")
        action = st.radio("Select Action", ["Add New Movie", "Edit Movie", "Remove Movie", "View All Movies"])

        if action == "Add New Movie":
            with st.form("add_movie"):
                title = st.text_input("Title")
                year = st.number_input("Release Year", 1900, 2030, 2020)
                duration = st.number_input("Duration (minutes)", 1, 300, 120)
                genres = st.multiselect("Genres", all_genres)
                desc = st.text_area("Description")

                if st.form_submit_button("Add Movie"):
                    new_id = f"M{len(engine.all_movies) + 1}"
                    new_movie = Movie(new_id, title, genres, year, duration, desc)
                    engine.add_movie(new_movie)
                    save_data(engine)
                    st.success(f"Added {title} (ID: {new_id})")

        elif action == "Edit Movie":
            mid = st.selectbox("Select movie to edit", list(engine.all_movies.keys()))
            movie = engine.get_movie_by_id(mid)
            if movie:
                new_title = st.text_input("Title", movie.title)
                new_year = st.number_input("Year", 1900, 2030, movie.release_year)
                if st.button("Update Movie"):
                    movie.title = new_title
                    movie.release_year = new_year
                    save_data(engine)
                    st.success("Updated!")

        elif action == "Remove Movie":
            mid = st.selectbox("Select movie to remove", list(engine.all_movies.keys()))
            if st.button("Remove", type="primary"):
                del engine.all_movies[mid]
                save_data(engine)
                st.success("Removed!")
                st.rerun()

        else:
            movies_data = []
            for m in engine.all_movies.values():
                movies_data.append({
                    "ID": m.movie_id,
                    "Title": m.title,
                    "Year": m.release_year,
                    "Genres": ", ".join(m.genre),
                    "Rating": f"{m.average_rating:.1f}/5",
                    "Views": m.view_count
                })
            st.table(movies_data)

    with tab2:
        st.subheader("Engagement Analytics")

        # System overview with big metrics
        col1, col2, col3, col4 = st.columns(4)
        total_views = sum(m.view_count for m in engine.all_movies.values())
        total_ratings = sum(m.rating_count for m in engine.all_movies.values())
        col1.metric(" Movies", len(engine.all_movies))
        col2.metric(" Users", len(engine.all_users))
        col3.metric(" Total Views", total_views)
        col4.metric(" Total Ratings", total_ratings)

        # Most-watched with medals
        st.write("** Most-Watched Movies**")
        most_watched = engine.get_most_watched_movies(5)
        max_views = most_watched[0].view_count if most_watched else 1

        for i, m in enumerate(most_watched, 1):
            col1, col2, col3 = st.columns([1, 3, 2])
            with col1:
                st.write(f"{get_medal(i)}")
            with col2:
                st.write(f"**{m.title}**")
                st.progress(m.view_count / max_views)
            with col3:
                st.write(f"**{m.view_count}** views")
                st.caption(f"{make_stars(m.average_rating)} {m.average_rating:.1f}★")

        st.markdown("---")

        # Top active users with ranking
        st.write("** Top Active Users (by Watch Count)**")
        active_users = engine.get_most_active_users(5)

        for i, (user, count) in enumerate(active_users, 1):
            with st.container(border=True):
                col1, col2, col3 = st.columns([1, 3, 2])
                with col1:
                    st.write(f"{get_medal(i)}")
                with col2:
                    st.write(f"**{user.name}**")
                    st.caption(f"Member since {user.user_id}")
                with col3:
                    st.write(f"**{count}** movies")
                    st.caption(f"{user.get_total_watch_time()} min watched")

        st.markdown("---")

        # Trending movies with score breakdown
        st.write("** Trending Movies (Trend Score Breakdown)**")
        trending = engine.get_trending_movies(5)

        for i, m in enumerate(trending, 1):
            with st.container(border=True):
                col1, col2 = st.columns([1, 4])
                with col1:
                    st.write(f"{get_medal(i)}")
                with col2:
                    st.write(f"**{m.title}**")
                    rating_comp = m.average_rating * 0.7
                    view_comp = min(m.view_count / 100, 5.0) * 0.3

                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        st.metric("Trend Score", f"{m.get_trending_score():.1f}")
                    with col_b:
                        st.caption(f"Rating (×0.7): {rating_comp:.1f}")
                        st.progress(rating_comp / 5.0)
                    with col_c:
                        st.caption(f"Views (×0.3): {view_comp:.1f}")
                        st.progress(view_comp / 5.0)
