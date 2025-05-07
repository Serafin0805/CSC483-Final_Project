from curses.ascii import isdigit

# import kagglehub
# path = kagglehub.dataset_download("carlosgdcj/genius-song-lyrics-with-language-information")
# print("Path to dataset files:", path)


import pandas as pd
import string
import nltk
import ssl
import certifi
import math
from openai import OpenAI
import os

# used to work around the nltk.download() code
ssl._create_default_https_context = ssl._create_unverified_context  # temporary workaround

nltk.download('punkt')
nltk.download('punkt_tab')
nltk.download('wordnet')
nltk.download('omw-1.4')

from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer


class IRSystem:

    def __init__(self):
        file_path = "./Song_files/12297par.parquet"
        self.df = pd.read_parquet(file_path)

        # we do not care about the language columns
        self.df.drop(columns=['language_cld3'], inplace=True)
        self.df.drop(columns=['language_ft'], inplace=True)
        self.df.drop(columns=['language'], inplace=True)
        # features and views are also non-important
        self.df.drop(columns=['features'], inplace=True)
        self.df.drop(columns=['views'], inplace=True)

        self.df['lyrics'] = self.df['lyrics'].str.replace(r'\[.*?\]', '', regex=True).str.replace(r'\s+', ' ',
                                                                                                  regex=True).str.strip()

        self.df["artist"] = self.df["artist"].str.lower()
        self.lemmatizer = WordNetLemmatizer()

        self.df['tokens'] = self.df['lyrics'].apply(self.tokenize_and_lemmatize)

        # Use lnc to weight terms in the documents:
        #   l: logarithmic tf
        #   n: no df
        #   c: cosine normalization
        self.raw_term_freq = {}
        # document frequency for the term
        self.doc_frequency = {}

        # number of documents in the collection
        self.N = 0

        # martix with the log weight of tf
        self.l = {}

        # matrix with the cosine
        self.c = {}

        for index, row in self.df.iterrows():
            doc_id = row['id']
            self.N += 1
            self.raw_term_freq[doc_id] = {}

            words = row['tokens']
            for word in words:
                if word not in self.doc_frequency:
                    self.doc_frequency[word] = set()
                    self.c[word] = float(0)
                    self.doc_frequency[word].add(doc_id)
                else:
                    self.doc_frequency[word].add(doc_id)

                if word not in self.raw_term_freq[doc_id]:
                    self.raw_term_freq[doc_id][word] = 1
                else:
                    self.raw_term_freq[doc_id][word] += 1

        # logarthmic weight calculation for matrix

        for doc_id in self.raw_term_freq:
            self.l[doc_id] = {}
            for word in self.raw_term_freq[doc_id]:
                raw = self.raw_term_freq[doc_id][word]
                weight = float((1 + math.log10(raw)))
                self.l[doc_id][word] = weight

        # can be put in the loop above
        norms = {}
        for doc_id in self.l:
            norm_sum = float(0)
            for word in self.l[doc_id]:
                norm_sum += float((self.l[doc_id][word]) ** 2)
            norms[doc_id] = float(math.sqrt(norm_sum))

        #could also be put in the the loop above
        self.normalized = {}
        for doc_id in self.l:
            self.normalized[doc_id] = {}
            for word in self.l[doc_id]:
                self.normalized[doc_id][word] = float(self.l[doc_id][word] / norms[doc_id])

    def tokenize_and_lemmatize(self, text):
        tokens = word_tokenize(text)
        tokens = [t.lower() for t in tokens if t.isalpha() or t.isdigit()]
        lemmas = [self.lemmatizer.lemmatize(token) for token in tokens]
        return lemmas

    def filtereddf(self, year, artist):
        filtered_df = self.df
        if year == '':
            year = '0'
        if year.isdigit() and len(year) == 4:
            if filtered_df["year"].astype(str).str.contains(str(year)).any():
                filtered_df = filtered_df[filtered_df['year'] == int(year)]

        if artist == '':
            artist = '!@#$%^&*'
        if filtered_df["artist"].str.contains(artist).any():
            filtered_df = filtered_df[filtered_df['artist'] == artist]
        return filtered_df["id"].tolist()

    def run_query(self, lyrics, year, artist):
        terms = lyrics.lower().split()
        artist = artist.lower()
        ranked, ai = self._run_query(terms, year, artist)
        return ranked,ai

    def _run_query(self, terms, year, artist):
        # Use ltn to weight terms in the query:
        #   l: logarithmic tf
        #   t: idf
        #   n: no normalization

        # Return the top-10 document for the query 'terms'
        query_tf = {}
        query_idf = {}
        # raw tf for the query
        for term in terms:
            if term not in query_tf:
                query_tf[term] = 1
            else:
                query_tf[term] += 1
        # calculate tf with log for the terms in the query
        for term in query_tf:
            if term not in self.doc_frequency:
                query_idf[term] = 0
            else:
                query_idf[term] = float(math.log10(self.N / len(self.doc_frequency[term])))
            query_tf[term] = float(1 + math.log10(query_tf[term]))

        query_w = {}
        for term in query_tf:
            query_w[term] = float(query_tf[term] * query_idf[term])
        x = 1
        idlist = self.filtereddf(year, artist)
        cosSims = []
        for doc in idlist:
            cossimnum = float(0)
            for term in query_w:
                if term not in self.normalized[doc]:
                    cossimnum += 0 * query_w[term]
                else:
                    cossimnum += float(self.normalized[doc][term] * query_w[term])
            cosSims.append((doc, cossimnum))

            if len(cosSims) > 10:
                cosSims.sort(key=self.sortbysim, reverse=True)
                cosSims = cosSims[:10]


        docid_list = [i[0] for i in cosSims]
        top10_df = self.df[self.df['id'].isin(docid_list)]
        top10_df = top10_df[["title", "artist","year"]]
        i = 1

        top10_str = ""
        top_hit_title = None
        top_hit_artist = None
        top_hit_year = None
        for row in top10_df.itertuples():
            if i == 1:
                top_hit_title = row.title
                top_hit_artist = row.artist
                top_hit_year = row.year
            top10_str += f"{i} : {row.title} ({row.year}) - {row.artist}\n"
            i += 1


        top10_json = top10_df.to_json()
        #aiout_str = "INACTIVE"
        aiout_str = self.rerankAI(top10_json, top_hit_title, top_hit_artist,top_hit_year)
        return top10_str, aiout_str

    def rerankAI(self, top10_json, song_name, artist_name, year):
        api_key = #MUST INPUT YOUR OWN API KEY
        client = OpenAI(api_key=ping_api_key)

        response = client.responses.create(
            model="gpt-4o-mini",
            instructions=(

                f"Your objective is to give me song info (artist, year, album, brief history) in less than 100 characters"
                # +1 modified ^^ line was first prompt 
                f"the song name is {song_name}"
                f"the artist is {artist_name}"
                f"and the year is {year}"
            ),
            input=f"Tell me about the song titled {song_name} from {artist_name} that came out in {year}"
        )
        return response.output_text

    def sortbysim(self, i):
        return i[1]