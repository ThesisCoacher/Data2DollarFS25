#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
sentiment_analysis_bert.py - Sentimentanalyse mit BERT für Bundestagsreden

Analysiert vorbereitete Token-Chunks (max. 500 Tokens) aus 'bundestag_reden_tokenized_chunks.csv'
und verarbeitet alle Texte mit bis zu 512 Tokens inkl. Sondertokens.

Datum: 04.05.2025
"""

import pandas as pd
import numpy as np
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
import matplotlib.pyplot as plt
import seaborn as sns
from tqdm import tqdm
import os

# Konfiguration
MODEL_NAME = "oliverguhr/german-sentiment-bert"
INPUT_FILE = "bundestag_reden_tokenized_chunks.csv"
OUTPUT_FILE = "bundestagsreden_chunks_sentiment.csv"
VISUALIZE_RESULTS = True

def main():
    print("\U0001f504 Initialisiere Sentiment-Analyse mit BERT...")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"\U0001f5a5️ Verwende Gerät: {device}")

    print(f"\U0001f4e6 Lade Modell '{MODEL_NAME}'...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME).to(device)

    sentiment_pipeline = pipeline("sentiment-analysis", model=model, tokenizer=tokenizer, device=0 if torch.cuda.is_available() else -1)

    print(f"\U0001f4c4 Lade Daten aus '{INPUT_FILE}'...")
    try:
        df = pd.read_csv(INPUT_FILE)
        print(f"\u2705 {len(df)} Einträge gefunden.")
    except Exception as e:
        print(f"\u274c Fehler beim Laden der Daten: {e}")
        return

    df_filtered = df[df["text"].notna() & (df["text"].str.len() > 20)].copy()
    print(f"\u2705 {len(df_filtered)} gültige Texte zur Analyse.")

    results = []

    print("\U0001f680 Analysiere Texte...")
    for _, row in tqdm(df_filtered.iterrows(), total=len(df_filtered)):
        text = row["text"]

        try:
            tokens = tokenizer.encode(text, add_special_tokens=True, truncation=False)
            token_count = len(tokens)
            if token_count > 512:
                print(f"\u26a0\ufe0f Übersprungen (zu lang): Zeile {row.name} mit {token_count} Tokens")
                continue

            result = sentiment_pipeline(text)[0]
            sentiment = result["label"]
            confidence = result["score"]

            probs = {
                "POSITIVE": confidence if sentiment == "POSITIVE" else 0.0,
                "NEUTRAL": confidence if sentiment == "NEUTRAL" else 0.0,
                "NEGATIVE": confidence if sentiment == "NEGATIVE" else 0.0,
            }

            results.append({
                **row,
                "sentiment": sentiment,
                "confidence": confidence,
                "token_count": token_count,
                "positive_prob": probs["POSITIVE"],
                "neutral_prob": probs["NEUTRAL"],
                "negative_prob": probs["NEGATIVE"]
            })

        except Exception as e:
            print(f"\u26a0\ufe0f Fehler bei Zeile {row.name}: {e}")

    if results:
        df_results = pd.DataFrame(results)
        df_results.to_csv(OUTPUT_FILE, index=False)
        print(f"\U0001f4c0 Ergebnisse gespeichert in '{OUTPUT_FILE}'")

        sentiment_counts = df_results["sentiment"].value_counts()
        print("\n\U0001f4ca Sentiment-Verteilung:")
        for sentiment, count in sentiment_counts.items():
            percentage = 100 * count / len(df_results)
            print(f"  {sentiment}: {count} ({percentage:.1f}%)")

        if VISUALIZE_RESULTS:
            print("\n\U0001f4c8 Erstelle Visualisierungen...")

            plt.figure(figsize=(10, 6))
            ax = sns.countplot(x="sentiment", data=df_results, palette=["green", "gray", "red"])
            plt.title("Verteilung der Sentiments in Bundestagsreden")
            plt.ylabel("Anzahl")
            plt.xlabel("Sentiment")

            for p in ax.patches:
                height = p.get_height()
                ax.text(p.get_x() + p.get_width()/2., height + 0.1,
                        f'{height} ({height/len(df_results)*100:.1f}%)',
                        ha="center")

            plt.tight_layout()
            plt.savefig("sentiment_verteilung.png")

            if "speaker_party" in df_results.columns:
                plt.figure(figsize=(12, 8))
                party_sentiment = pd.crosstab(
                    df_results["speaker_party"],
                    df_results["sentiment"],
                    normalize="index"
                ) * 100

                party_sentiment.plot(kind="bar", stacked=True,
                                     colormap="RdYlGn", figsize=(12, 8))
                plt.title("Sentiment-Verteilung nach Partei")
                plt.ylabel("Prozent")
                plt.xlabel("Partei")
                plt.legend(title="Sentiment")
                plt.tight_layout()
                plt.savefig("sentiment_nach_partei.png")

            print("\u2705 Visualisierungen erstellt.")
    else:
        print("\u26a0\ufe0f Keine Ergebnisse zur Speicherung.")

    print("\u2705 Analyse abgeschlossen!")

if __name__ == "__main__":
    main()
