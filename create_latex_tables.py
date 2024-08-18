from tabulate import tabulate
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt
import pickle

def generate_latex_table(data, headers=None, caption=None, label=None):
    # Start the table environment
    latex = "\\begin{table}[h!]\n"
    latex += "\\centering\n"

    if caption:
        latex += f"\\caption{{{caption}}}\n"
    if label:
        latex += f"\\label{{{label}}}\n"

    # Start the tabular environment
    n_cols = len(data[0])
    latex += "\\begin{tabular}{" + " | ".join(["c"] * n_cols) + "}\n"
    latex += "\\hline\n"

    # Add the header row
    if headers:
        latex += " & ".join(headers) + " \\\\\n"
        latex += "\\hline\n"

    # Add the data rows
    for row in data:
        latex += " & ".join(map(str, row)) + " \\\\\n"
        latex += "\\hline\n"

    # End the tabular environment
    latex += "\\end{tabular}\n"

    # End the table environment
    latex += "\\end{table}\n"

    return latex

scenario_name = 1
experiment_results = f"../results/{scenario_name}"
algorithms = ["static", "vucb1-per-hop-corr"]
files = [f'{experiment_results}/{string}_OpenRTiST.pkl' for string in algorithms]
print(files)

all_data = []
for file in files:
    with open(file, 'rb') as file:
        dictionary = pickle.load(file)
        headers = list(dictionary.keys())
        values = list(dictionary.values())
        values = [int(v) for v in values]
        all_data.append(values)

print(headers)
print(all_data)

table = tabulate(all_data, headers)
print(table)

# Create a figure and axis to render the table
fig, ax = plt.subplots(figsize=(8, 2))  # Adjust the figure size as needed
ax.axis('tight')
ax.axis('off')

# Display the table as text
ax.table(cellText=all_data, colLabels=headers, cellLoc='center', loc='center', edges='open')

# Save the table as a PDF
with PdfPages(f"{experiment_results}/comparisons.pdf") as pdf:
    pdf.savefig(fig, bbox_inches='tight')
plt.close(fig)