from flask import Flask, render_template, request, session, redirect, url_for
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import cx_Oracle

app = Flask(__name__)
app.secret_key = 'your_secret_key'

def connect_to_oracle():
    connection = cx_Oracle.connect("SYSTEM/123456@localhost:1521/xe")
    return connection

def register_user(name, username, password, birthdate):
    connection = connect_to_oracle()
    cursor = connection.cursor()
    sql = "INSERT INTO MOVIE_USER (NAME, USERNAME, PASSWORD, BIRTHDATE) VALUES (:1, :2, :3, :4)"
    cursor.execute(sql, (name, username, password, birthdate))
    connection.commit()
    cursor.close()
    connection.close()

def get_user(username):
    connection = connect_to_oracle()
    cursor = connection.cursor()
    sql = "SELECT USERNAME, PASSWORD FROM MOVIE_USER WHERE USERNAME = :1"
    cursor.execute(sql, (username,))
    user = cursor.fetchone()
    cursor.close()
    connection.close()
    return user

# 사용자가 입력한 영화 제목을 기반으로 유사한 장르의 영화를 찾는 함수 정의
# Term Frequency-Inverse Document Frequency
# 자연어 처리에서 텍스트 데이터를 수치화하는 데 사용되는 방법 중 하나
def get_similar_movies(movie_title):
    connection = connect_to_oracle()
    cursor = connection.cursor()
    # 모든 영화의 제목과 장르를 선택하는 SQL 쿼리 작성
    sql = "SELECT TITLE, GENRE FROM MOVIE"
    cursor.execute(sql)
    movies = cursor.fetchall()
    cursor.close()
    connection.close()
    # 가져온 결과에서 영화 제목을 추출하여 리스트로 저장
    movie_titles = [movie[0] for movie in movies]
    # 가져온 결과에서 영화 장르를 추출하여 리스트로 저장. 장르 정보가 없는 경우 빈 문자열로 처리
    movie_genres = [movie[1] if movie[1] is not None else '' for movie in movies]
    try:
        vectorizer = TfidfVectorizer()
        # 영화 장르를 TF-IDF 벡터로 변환
        movie_vectors = vectorizer.fit_transform(movie_genres)
        # 사용자가 입력한 영화 제목의 인덱스를 찾음
        movie_index = movie_titles.index(movie_title)
        # 해당 영화의 TF-IDF 벡터를 가져옴
        movie_vector = movie_vectors[movie_index]
        # 코사인 유사도를 사용하여 입력 영화와 다른 모든 영화와의 유사도를 계산
        cosine_similarities = cosine_similarity(movie_vector, movie_vectors).flatten()
        # 계산된 유사도를 기준으로 상위 10개 영화의 인덱스를 가져옴
        similar_movie_indices = cosine_similarities.argsort()[::-1][1:11]
        # 상위 10개 영화의 제목을 반환
        return [movie_titles[i] for i in similar_movie_indices]
    except Exception as e:
        print(f"Error in get_similar_movies: {e}")
        return []

def get_movie_image(movie_title):
    connection = connect_to_oracle()
    cursor = connection.cursor()
    sql = "SELECT POSTER_URL FROM MOVIE WHERE TITLE = :1 ORDER BY 1"
    cursor.execute(sql, (movie_title,))
    image_url = cursor.fetchone()[0]
    cursor.close()
    connection.close()
    return image_url

def add_favorite(username, movie_titles):
    connection = connect_to_oracle()
    cursor = connection.cursor()
    sql = "INSERT INTO FAVORITES (USERNAME, MOVIE_TITLE) VALUES (:1, :2)"
    for movie_title in movie_titles:
        cursor.execute(sql, (username, movie_title))
    connection.commit()
    cursor.close()
    connection.close()

def get_favorites(username):
    connection = connect_to_oracle()
    cursor = connection.cursor()
    sql = "SELECT MOVIE_TITLE FROM FAVORITES WHERE USERNAME = :1"
    cursor.execute(sql, (username,))
    favorites = [row[0] for row in cursor.fetchall()]
    cursor.close()
    connection.close()
    return favorites

def delete_favorite(username, movie_titles):
    connection = connect_to_oracle()
    cursor = connection.cursor()
    for movie_title in movie_titles:
        sql = "DELETE FROM FAVORITES WHERE USERNAME = :1 AND MOVIE_TITLE = :2"
        cursor.execute(sql, (username, movie_title))
    connection.commit()
    cursor.close()
    connection.close()

@app.route('/', methods=['GET'])
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = get_user(username)
        if user and user[1] == password:
            session['username'] = username
            return redirect(url_for('index'))
        else:
            return 'Invalid username or password'
    return render_template('login.html')

@app.route('/index', methods=['GET'])
def index():
    if 'username' in session:
        username = session['username']
        return render_template('index.html', username=username)
    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('home'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        username = request.form['username']
        password = request.form['password']
        birthdate = request.form['birthdate']
        register_user(name, username, password, birthdate)
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/recommend', methods=['POST'])
def recommend():
    if 'username' in session:
        username = session['username']
        movie_title = request.form['movie']
        similar_movies = get_similar_movies(movie_title)
        similar_movies_images = [get_movie_image(movie) for movie in similar_movies]
        return render_template('index.html', username=username, input_movie=movie_title, similar_movies=zip(similar_movies, similar_movies_images))
    return redirect(url_for('login'))

@app.route('/favorites', methods=['GET', 'POST'])
def favorites():
    if 'username' in session:
        username = session['username']
        if request.method == 'POST':
            movie_titles = request.form.getlist('movie[]')  # 여러 영화 제목을 리스트로 가져옵니다.
            if 'delete' in request.form:
                delete_favorite(username, movie_titles)  # 수정된 부분
            else:
                add_favorite(username, movie_titles)
        favorites = get_favorites(username)
        favorite_images = [get_movie_image(movie) for movie in favorites]
        return render_template('favorites.html', username=username, favorites=zip(favorites, favorite_images))
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)