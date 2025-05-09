#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
split_texts_to_chunks.py - Aufteilen langer Texte in Token-Blöcke

Dieses Skript teilt die Texte aus der Datei 'bundestag_reden_sentiment_30sitzungen.csv'
in Blöcke von maximal 512 Tokens auf und fügt eine ID-Spalte hinzu, um zusammengehörige
Textblöcke zu kennzeichnen.

Datum: 04.05.2025
"""

import pandas as pd
from transformers import AutoTokenizer
import re
import os
from tqdm import tqdm

# Konfiguration
INPUT_FILE = "bundestag_reden_sentiment_30sitzungen.csv"
OUTPUT_FILE = "bundestag_reden_tokenized_chunks.csv"
MODEL_NAME = "oliverguhr/german-sentiment-bert"
MAX_TOKENS = 500
OVERLAP = 50

def clean_text(text):
    if not isinstance(text, str):
        return ""
    return re.sub(r'\s+', ' ', text).strip()

def main():
    print(f"📄 Lade Datei '{INPUT_FILE}'...")
    try:
        df = pd.read_csv(INPUT_FILE)
        print(f"✅ Erfolgreich geladen: {len(df)} Einträge")
    except Exception as e:
        print(f"❌ Fehler beim Laden: {e}")
        return

    print(f"📦 Lade Tokenizer '{MODEL_NAME}'...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    df_valid = df[df["text"].notna()].copy()
    print(f"✅ {len(df_valid)} gültige Texte gefunden")

    chunks = []
    chunk_id = 0

    print("🔄 Teile Texte in Token-Blöcke...")
    for idx, row in tqdm(df_valid.iterrows(), total=len(df_valid)):
        text = clean_text(row["text"])
        text_id = f"text_{idx}"
        tokens = tokenizer.encode(text, add_special_tokens=True)

        if len(tokens) <= MAX_TOKENS:
            chunk_data = {
                "chunk_id": chunk_id,
                "text_id": text_id,
                "chunk_number": 1,
                "total_chunks": 1,
                "text": text,
                "token_count": len(tokens)
            }
            for col in df.columns:
                if col != "text":
                    chunk_data[col] = row[col]
            chunks.append(chunk_data)
            chunk_id += 1
        else:
            chunk_parts = []
            for i in range(0, len(tokens), MAX_TOKENS - OVERLAP):
                end_idx = min(i + MAX_TOKENS, len(tokens))
                chunk_tokens = tokens[i:end_idx]

                chunk_text = tokenizer.convert_tokens_to_string(tokenizer.convert_ids_to_tokens(chunk_tokens))

                chunk_parts.append({
                    "tokens": chunk_tokens,
                    "text": chunk_text,
                    "token_count": len(chunk_tokens)
                })

                if end_idx == len(tokens):
                    break

            for i, part in enumerate(chunk_parts):
                chunk_data = {
                    "chunk_id": chunk_id,
                    "text_id": text_id,
                    "chunk_number": i + 1,
                    "total_chunks": len(chunk_parts),
                    "text": part["text"],
                    "token_count": part["token_count"]
                }
                for col in df.columns:
                    if col != "text":
                        chunk_data[col] = row[col]
                chunks.append(chunk_data)
                chunk_id += 1

    df_chunks = pd.DataFrame(chunks)

    total_original_tokens = df_valid["text"].apply(
        lambda x: len(tokenizer.encode(x, add_special_tokens=True))
    ).sum()
    total_chunked_tokens = df_chunks["token_count"].sum()

    print(f"\n📊 Statistik:")
    print(f"  - Ursprüngliche Texte: {len(df_valid)}")
    print(f"  - Erzeugte Chunks: {len(df_chunks)}")
    print(f"  - Durchschnittliche Chunks pro Text: {len(df_chunks) / len(df_valid):.2f}")
    print(f"  - Ursprüngliche Token-Anzahl: {total_original_tokens}")
    print(f"  - Token-Anzahl nach Chunking: {total_chunked_tokens}")
    print(f"  - Token-Overhead durch Überlappung: {(total_chunked_tokens - total_original_tokens) / total_original_tokens * 100:.2f}%")

    assert all(df_chunks["token_count"] <= 500), "❌ Es gibt Chunks mit mehr als 512 Tokens!"

    df_chunks.to_csv(OUTPUT_FILE, index=False)
    print(f"\n📀 Ergebnis gespeichert als '{OUTPUT_FILE}'")
    print("✅ Aufteilen abgeschlossen!")

if __name__ == "__main__":
    main()
