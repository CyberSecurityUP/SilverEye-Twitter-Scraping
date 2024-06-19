import tweepy
import csv
import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd
import threading
import tkinter as tk
from tkinter import ttk
import cachetools
import webbrowser

current_hashtag = None

# Insira suas próprias credenciais obtidas ao criar uma conta de desenvolvedor no Twitter
API_KEY = ""
API_SECRET_KEY = ""
ACCESS_TOKEN = ""
ACCESS_SECRET_TOKEN = ""

# Função de autenticação
def authenticate(api_key, api_secret_key, access_token, access_secret_token):
    auth = tweepy.OAuthHandler(api_key, api_secret_key)
    auth.set_access_token(access_token, access_secret_token)
    return tweepy.API(auth)

# Função para buscar tweets pela hashtag
def search_tweets(api, hashtag, count=10, lang="pt-br"):
    tweets = api.search_tweets(q=hashtag, count=count, lang=lang)
    return tweets

def tweets_to_dataframe(tweets):
    data = []
    for tweet in tweets:
        data.append([tweet.user.screen_name, tweet.text])
    return pd.DataFrame(data, columns=["Username", "Tweet"])

def hashtags_from_tweets(tweets):
    hashtags = []
    for tweet in tweets:
        for hashtag in tweet.entities["hashtags"]:
            hashtags.append(hashtag["text"].lower())
    return hashtags

cache = cachetools.TTLCache(maxsize=100, ttl=300)

def cached_search_tweets(api, hashtag, count=10, lang="pt-br"):
    if hashtag not in cache:
        cache[hashtag] = search_tweets(api, hashtag, count, lang)
    return cache[hashtag]

def create_dashboard(api, hashtag_var):
    global current_hashtag
    current_hashtag = hashtag_var.get()

    # Criar o aplicativo Dash
    app = dash.Dash(__name__)

    # Definir o layout do aplicativo Dash
    app.layout = html.Div([
        html.H1("Dashboard de Tweets"),
        html.H3("Criado por Joas"),
        dcc.Tabs([
            dcc.Tab(label='Gráficos', children=[
                html.H3("Quantidade de Tweets por Hashtag"),
                dcc.Graph(id="hashtag-count-graph"),
                html.H3("Quantidade de Tweets por Usuário"),
                dcc.Graph(id="user-tweet-count-graph"),
            ]),
            dcc.Tab(label='Links dos Tweets', children=[
                html.H3("Links dos Tweets"),
                dash_table.DataTable(
                    id='tweet-links-table',
                    columns=[
                        {"name": "Usuário", "id": "Username"},
                        {"name": "Tweet", "id": "Tweet"},
                        {"name": "Link", "id": "Link"}
                    ],
                    data=[],
                )
            ]),
        ]),
        dcc.Interval(
            id="interval-component",
            interval=30*1000,  # Atualizar a cada 30 segundos
            n_intervals=0
        )
    ])

    @app.callback(Output("tweet-links-table", "data"),
                  Input("interval-component", "n_intervals"))
    def update_tweet_links_table(n_intervals):
        global current_hashtag
        tweet_count = 10
        current_hashtag = hashtag_var.get()
        results = cached_search_tweets(api, current_hashtag, tweet_count)
        df = tweets_to_dataframe(results)

        def get_tweet_url(username):
            for tweet in results:
                if tweet.user.screen_name == username:
                    return f"https://twitter.com/{username}/status/{tweet.id}"
            return None

        df["Link"] = df["Username"].apply(get_tweet_url)
        return df.to_dict('records')

    @app.callback(Output("hashtag-count-graph", "figure"),
                  Input("interval-component", "n_intervals"))
    def update_hashtag_count_graph(n_intervals):
        global current_hashtag
        new_hashtag = hashtag_var.get()
        if new_hashtag != current_hashtag:
            current_hashtag = new_hashtag
            create_dashboard(api, hashtag_var)
        tweet_count = 10
        results = cached_search_tweets(api, current_hashtag, tweet_count)

        hashtags = hashtags_from_tweets(results)

        hashtag_counts = pd.Series(hashtags).value_counts().reset_index()
        hashtag_counts.columns = ["Hashtag", "Tweets"]

        # Criar um gráfico de barras usando Plotly Express
        fig = px.bar(hashtag_counts, x="Hashtag", y="Tweets", title="Quantidade de Tweets por Hashtag")

        return fig

    @app.callback(Output("user-tweet-count-graph", "figure"),
                  Input("interval-component", "n_intervals"))
    def update_user_tweet_count_graph(n_intervals):
        global current_hashtag
        hashtag_var = current_hashtag
        current_hashtag = hashtag_var
        tweet_count = 10
        results = cached_search_tweets(api, current_hashtag, tweet_count)
        df = tweets_to_dataframe(results)

        # Agrupar a quantidade de tweets por usuário
        user_tweet_counts = df["Username"].value_counts().reset_index()
        user_tweet_counts.columns = ["Username", "Tweets"]

        # Criar um gráfico de barras usando Plotly Express
        fig = px.bar(user_tweet_counts, x="Username", y="Tweets", title="Quantidade de Tweets por Usuário")

        return fig

    # Iniciar o servidor Dash em uma thread separada
    def run_dash():
        app.run_server(debug=True, use_reloader=False)

    threading.Thread(target=run_dash).start()

def toggle_theme():
    if root.tk.call("ttk::style", "theme", "use") == "default":
        root.tk.call("ttk::style", "theme", "use", "alt")
    else:
        root.tk.call("ttk::style", "theme", "use", "default")

def main():
    global root
    api = authenticate(API_KEY, API_SECRET_KEY, ACCESS_TOKEN, ACCESS_SECRET_TOKEN)

    # Criar janela Tkinter
    root = tk.Tk()
    root.title("SilverEye Twitter Scraping")

    # Adicionar label e entry para inserir hashtag
    ttk.Label(root, text="Hashtag:").grid(row=0, column=0)
    hashtag_var = tk.StringVar()
    hashtag_entry = ttk.Entry(root, textvariable=hashtag_var)
    hashtag_entry.grid(row=0, column=1)

    # Botão para iniciar o dashboard
    start_button = ttk.Button(root, text="Iniciar Dashboard", command=lambda: update_current_hashtag(api, hashtag_var, create_dashboard))
    start_button.grid(row=1, column=0)

    # Botão para alternar o tema
    theme_button = ttk.Button(root, text="Alternar Tema", command=toggle_theme)
    theme_button.grid(row=1, column=1)

    # Botão para fechar a aplicação
    close_button = ttk.Button(root, text="Fechar", command=root.quit)
    close_button.grid(row=1, column=2)

    url = "http://127.0.0.1:8050/"
    webbrowser.open_new_tab(url)

    # Iniciar loop Tkinter
    root.mainloop()

def update_current_hashtag(api, hashtag, dashboard_func):
    global current_hashtag
    if isinstance(hashtag, str):  # Check if hashtag is a string
        hashtag_var = tk.StringVar()
        hashtag_var.set(hashtag)
        hashtag = hashtag_var
    else:
        hashtag_var = hashtag
    if not hashtag:
        messagebox.showerror("Erro", "Por favor, insira uma hashtag válida.")
        return

    # Atualizar a variável current_hashtag
    current_hashtag = hashtag.get()

    # Chame a função dashboard_func passando o argumento hashtag
    dashboard_func(api, hashtag_var)

if __name__ == "__main__":
    main()
    api = authenticate(API_KEY, API_SECRET_KEY, ACCESS_TOKEN, ACCESS_SECRET_TOKEN)
    hashtag_var = tk.StringVar()
    create_dashboard(api, hashtag_var)
