import re
import os
import argparse

def format_for_latex(text):
    r"""
    Esegue il refactoring del testo convertendo solo la matematica inline.
    
    Converte i delimitatori \( ... \) nel formato $ ... $, ma mantiene
    invariati i blocchi di equazioni display \[ ... \] per preservare
    la compatibilità con i motori di rendering LaTeX standard.
    
    Args:
        text (str): Il contenuto testuale del file Markdown originale.
        
    Returns:
        str: Il testo con la sola matematica inline convertita e spazi puliti.
    """
    # Converti SOLO Inline Math: \( ... \) -> $...$
    text = re.sub(r'\\\(\s*(.*?)\s*\\\)', r'$\1$', text)
    
    return text.strip()

def process_file(filepath):
    """
    Legge un file .md, applica la conversione LaTeX-style e sovrascrive il file.
    
    Args:
        filepath (str): Il percorso del file da processare.
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    new_content = format_for_latex(content)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"✅ Formattato: {os.path.basename(filepath)}")

def main():
    """
    Gestisce l'interfaccia CLI per la formattazione selettiva in stile LaTeX.
    """
    parser = argparse.ArgumentParser(description="Formatta file MD per LaTeX (Solo Inline Math)")
    
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