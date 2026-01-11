import re
import os
import argparse

def format_for_obsidian(text):
    r"""
    Converte i delimitatori matematici LaTeX standard nel formato supportato da Obsidian.
    
    Esegue le seguenti sostituzioni:
    - Trasforma i blocchi di equazioni (Display Math) da \[ ... \] a $$ ... $$.
    - Trasforma la matematica in riga (Inline Math) da \( ... \) a $ ... $.
    
    Args:
        text (str): Il contenuto testuale del file Markdown originale.
        
    Returns:
        str: Il testo convertito con la sintassi matematica di Obsidian, 
             privato di spazi bianchi superflui all'inizio e alla fine.
    """
    # Converti Display Math: \[ ... \] -> $$...$$
    text = re.sub(r'\\\[\s*(.*?)\s*\\\]', r'$$\1$$', text, flags=re.DOTALL)
    
    # Converti Inline Math: \( ... \) -> $...$
    text = re.sub(r'\\\(\s*(.*?)\s*\\\)', r'$\1$', text)
    
    return text.strip()

def process_file(filepath):
    """
    Legge un singolo file Markdown, ne converte la sintassi e sovrascrive l'originale.
    
    Questa funzione gestisce l'intero ciclo di vita del file: apertura,
    applicazione della formattazione tramite format_for_obsidian e salvataggio.
    
    Args:
        filepath (str): Il percorso completo del file .md da processare.
        
    Raises:
        IOError: Se si verificano problemi durante la lettura o la scrittura del file.
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    new_content = format_for_obsidian(content)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"✅ Formattato: {os.path.basename(filepath)}")

def main():
    """
    Punto di ingresso dello script per l'interfaccia a riga di comando (CLI).
    
    Configura il parser degli argomenti, verifica l'esistenza del percorso fornito
    e decide se processare un singolo file o scansionare una cartella alla ricerca
    di tutti i file Markdown (.md).
    """
    parser = argparse.ArgumentParser(description="Formatta file MD per Obsidian (File singolo o Cartella)")
    
    # Supporto per posizionale e flag -p/--path
    parser.add_argument("pos_path", nargs="?", help="Percorso del file .md o della cartella")
    parser.add_argument("-p", "--path", help="Percorso del file .md o della cartella (tramite flag)")
    
    args = parser.parse_args()

    # Logica di selezione del percorso
    target = args.path if args.path else args.pos_path

    if not target:
        print("❌ Errore: Devi specificare un percorso. Esempio: python latex_formatter.py ./note")
        return

    if not os.path.exists(target):
        print(f"❌ Errore: Il percorso '{target}' non esiste.")
        return

    # Caso 1: CARTELLA
    if os.path.isdir(target):
        files = [f for f in os.listdir(target) if f.endswith(".md")]
        if not files:
            print(f"⚠️ Nessun file .md trovato in: {target}")
            return
        for filename in files:
            process_file(os.path.join(target, filename))
        print(f"\n✨ Finito! Processati {len(files)} file nella cartella.")

    # Caso 2: FILE SINGOLO
    elif os.path.isfile(target):
        if target.endswith(".md"):
            process_file(target)
        else:
            print(f"❌ Errore: Il file '{target}' non è un file .md")

if __name__ == "__main__":
    main()