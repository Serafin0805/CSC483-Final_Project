import IRSystem

ir_system = IRSystem.IRSystem()

# main_gui.py

import tkinter as tk
from tkinter import ttk
import sys
import io
from IRSystem import IRSystem

ir_system = IRSystem()

def on_submit():
    lyrics = lyrics_var.get()
    artist = artist_var.get()
    year = year_var.get()

    output_text.delete("1.0", tk.END)
    ranked_text.delete("1.0", tk.END)

    try:
        buffer = io.StringIO()
        sys.stdout = sys.stderr = buffer

        system_output, ai_out_put_text = ir_system.run_query(lyrics, year, artist)



        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__

        output_text.insert(tk.END, f"{buffer.getvalue()}\n{system_output}")
        ranked_text.insert(tk.END, ai_out_put_text)
        buffer.close()
    except Exception as e:
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        output_text.insert(tk.END, f"Error: {e}")

# GUI Setup
root = tk.Tk()
root.title("Lyrics Search")
root.geometry("800x800")

lyrics_var = tk.StringVar()
artist_var = tk.StringVar()
year_var = tk.StringVar()

ttk.Label(root, text="Search Lyrics:").pack(anchor="w", padx=10, pady=(10, 0))
ttk.Entry(root, textvariable=lyrics_var).pack(fill="x", padx=10)

ttk.Label(root, text="Artist:").pack(anchor="w", padx=10, pady=(10, 0))
ttk.Entry(root, textvariable=artist_var).pack(fill="x", padx=10)

ttk.Label(root, text="Year:").pack(anchor="w", padx=10, pady=(10, 0))
ttk.Entry(root, textvariable=year_var).pack(fill="x", padx=10)

ttk.Button(root, text="Search", command=on_submit).pack(pady=10)

ttk.Label(root, text="Top 10 Songs:").pack(anchor="w", padx=10)
output_text = tk.Text(root, height=20, wrap="word")
output_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))

ttk.Label(root, text="Overview of Top Hit:").pack(anchor="w", padx=10)
ranked_text = tk.Text(root, height=10, wrap="word")
ranked_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))

root.mainloop()