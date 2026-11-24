import pandas as pd
import os
import tkinter as tk
from tkinter import filedialog, messagebox
import json
from pathlib import Path

FILE_DIR = Path(__file__).resolve().parent

# cleaning functions
def full_clean(data: pd.DataFrame, parameters, f): 
    strip = parameters["strip"]
    rename_col = parameters["rename_col"]
    rm_tf = parameters["rm_tf"]
    rm_col = parameters["rm_col"]
    rm_row = parameters["rm_row"]
    rm_dupe_col = parameters["rm_dupe_col"]
    rm_dupe_row = parameters["rm_dupe_row"]
    rm_outliers = parameters["rm_outliers"]
    quant_size = parameters["quant_size"]
    protected_cols = parameters["protected_cols"]

    f.write(f"Parameters:\n")
    f.write(f"Strip whitespace: {strip}\n")
    f.write(f"Normalize column names to snake case: {rename_col}\n")
    f.write(f"Remove columns or rows due to missingness: {rm_tf}\n")
    f.write(f"Column missingness threshold to delete: {rm_col}\n")
    f.write(f"Row missingness threshold to delete: {rm_row}\n")
    f.write(f"Remove duplicate columns: {rm_dupe_col}\n")
    f.write(f"Remove duplicate rows: {rm_dupe_row}\n")
    f.write(f"Remove outliers: {rm_outliers}\n")
    f.write(f"Outlier quantile size: {quant_size}\n")
    f.write(f"Protected columns: {protected_cols}\n")
    f.write("\n")

    # strip whitespace from strings
    if strip:
        cols_before = data.columns.copy()
        data.columns = data.columns.str.strip()
        data_before = data.copy()
        data = data.map(lambda x: x.strip() if isinstance(x, str) else x)

        # adds the column name post-whitespace removal to protected_cols
        if protected_cols:
            for col in cols_before:
                if col in protected_cols and isinstance(col, str):
                    protected_cols.add(col.strip())

        diff = ((data != data_before) & ~(data.isna() & data_before.isna())).values.sum() + len(data.columns.difference(cols_before))
        f.write(f"Removed whitespace from {diff} cells\n")
    else:
        f.write("Flagged: whitespace removal not performed, recommended to check whitespace manually\n")
    f.write("\n")
    
    # standardize col names into snake case
    if rename_col:
        # so for a reason unknown to your humble programmer, deep needs to be set to true here unlike everywhere else
        # otherwise the for loop also affects colums_before
        columns_before = data.columns.copy(deep = True)

        # all chars that are or will be underscores
        uscores = {"_", " ", "-"}

        for col in data.columns:
            to_snake = ""
            prev = ""
            for char in col:
                if prev.islower() and char.isupper():
                    to_snake += "_" + char.lower()
                # prevents multiple underscores from appearing in sequence
                elif prev in uscores and char in uscores:
                    continue
                else:
                    to_snake += char
                prev = char
            to_snake = to_snake.strip().lower().replace(" ", "_").replace("-", "_").strip("_")

            if protected_cols and col in protected_cols:
                protected_cols.add(to_snake)

            data.rename(columns = {col: to_snake}, inplace = True)

        renamed_cols = columns_before.difference(data.columns).tolist()
        f.write(f"Renamed columns: {renamed_cols}\n")
    else:
        f.write("Flagged: no column name normalization performed, recommended to check name style manually\n")
    f.write("\n")

    if rm_tf:
        # removes columns with a percent of missing values above the threshold
        columns_before = data.columns.copy()
        # edge case where data with no rows gets all column names deleted
        if len(data) != 0:
            if not protected_cols:
                if rm_col != 0:
                    data = data.loc[:, data.isna().mean() <= rm_col]
                # if the threshold is 0, just remove all empty cols
                data = data.dropna(how = "all", axis = 1)
            else:
                cols_to_drop = []
                if rm_col != 0:
                    cols_to_drop = data.columns[data.isna().mean() >= rm_col].tolist()
                cols_to_drop.extend(data.columns[data.isna().all()].tolist())

                # removes columns from cols_to_drop if they are protected
                cols_to_drop = [col for col in cols_to_drop if col not in protected_cols]
                data = data.drop(columns = cols_to_drop)
            
        removed_cols = columns_before.difference(data.columns).tolist()
        f.write(f"Dropped columns: {removed_cols} due to missing values\n")
        f.write("\n")

        # removes rows with a percent of missing values above the threshold
        len_before = len(data)
        if rm_row != 0:
            data = data[data.isna().mean(axis=1) <= rm_row]
            data.dropna(how = "all", inplace = True)
        else:
            # if the threshold is 0, remove all rows with a missing value
            data = data.dropna()
        f.write(f"Dropped {len_before - len(data)} rows due to missing values\n")
        f.write("\n")
    else:
        f.write("Flagged: no columns or rows removed due to missingness, recommended to check manually, see more info below\n")

        # some harmless checks to flag missing data
        columns_before = data.columns.copy()

        after_col_rm = data.loc[:, data.isna().mean() <= 0.5]

        flag_cols = columns_before.difference(after_col_rm.columns).tolist()
        f.write(f"Flagged: columns {flag_cols} have a missingness above 50%,\n")

        after_col_rm_full = data.columns[data.isna().all()].tolist()
        f.write(f"and columns {after_col_rm_full} are completely empty\n")

        len_before = len(data)
        after_row_rm = data[data.isna().mean(axis=1) <= 0.5]
        f.write(f"Flagged: {len_before - len(after_row_rm)} rows have a missingness above 50%,\n")

        after_row_rm_full = data.dropna()
        f.write(f"and {len_before - len(after_row_rm_full)} rows have missing values (may be skewed due to fully missing columns)\n")
        f.write("\n")

    # removes duplicate columns
    if rm_dupe_col:
        columns_before = data.columns.copy()
        # the col duplication removal bugs out if there there's no data
        if len(data) != 0:
            # roundabout solution because original flipped the df, removed dupes, and flipped it back BUT doing this changed all cols to "object" type
            # this solution keeps the types by flipping the data, testing duplicates, then making a mask using that check bc it returns a boolean series
            if not protected_cols:
                data = data.loc[:, ~data.T.duplicated()]
            else:
                dupe_cols = data.columns[data.T.duplicated()]

                columns_to_drop = [col for col in dupe_cols if col not in protected_cols]

                data = data.drop(columns = columns_to_drop)

        removed_cols = columns_before.difference(data.columns).tolist()
        f.write(f"Dropped columns: {removed_cols} due to them being duplicates\n")
    else:
        f.write("Flagged: no column duplication removals performed, recommended to check duplicate columns manually, see more info below\n")

        columns_before = data.columns.copy()
        after_dupe_rm = data.T.drop_duplicates().T

        flagged_dupe_cols = columns_before.difference(after_dupe_rm.columns).tolist()
        f.write(f"Flagged: columns {flagged_dupe_cols} are duplicates\n")
    f.write("\n")

    # removes duplicate rows
    if rm_dupe_row:
        len_before = len(data)
        data.drop_duplicates(inplace = True)

        f.write(f"Dropped {len_before - len(data)} rows due to them being duplicates\n")
    else:
        f.write("Flagged: no row duplication removals performed, recommended to check duplicate rows manually, see more info below\n")
        len_before = len(data)
        after_dupe_r_rm = data.drop_duplicates()
        f.write(f"Flagged: {len_before - len(after_dupe_r_rm)} rows are duplicates\n")

    f.write("\n")

    if rm_outliers:
        len_before = len(data)
        numeric_data = data.select_dtypes(include = "number")
        if protected_cols:
            # errors=ignore since drop throws an error if the col doesn't exist in df, such as if the protected col isn't numeric here
            numeric_data.drop(columns = protected_cols, inplace = True, errors = "ignore")
        outlier_indices = set()
        for col in numeric_data.columns:
            quantile1 = numeric_data[col].quantile(quant_size)
            quantile2 = numeric_data[col].quantile(1 - quant_size)
            iqr = quantile2 - quantile1

            # ran into an issue before where a ton of rows would get vaporized, but by saving the indices it means rows that are outliers
            # in more than one column get removed at the end instead of others taking their place iteratively
            outlier_rows = numeric_data.index[(numeric_data[col] < quantile1 - 1.5 * iqr) | (numeric_data[col] > quantile2 + 1.5 * iqr)]
            outlier_indices.update(outlier_rows)

        if len_before - len(outlier_indices) >= len_before * 0.5:
            data = data.drop(index = outlier_indices)
            f.write(f"Dropped {len(outlier_indices)} potential outlier rows\n")
        else:
            f.write("Flagged: length of remaining data too small to remove outliers, recommended to check for outliers manually\n") 
    else:
        f.write("Flagged: no outlier removal performed, recommended to check for outliers manually\n")

    # this fixes ".0" being appended to all numbers even if they were originally int
    num_cols = data.select_dtypes(include = "float").columns
    if len(num_cols) != 0:
        for col in num_cols:
            float_int_check = data[col].dropna()
            if (float_int_check % 1 == 0).all():
                data[col] = data[col].astype("Int64")
    
    return data 

def read_config(protected_cols):
    config_path = FILE_DIR/"config"/"config.json"
    with open(config_path, "r") as f:
        parameters = json.load(f)
    parameters["protected_cols"] = protected_cols
    return parameters

def custom_load(data, f, protected_cols):
    # initially this function saved all return values individually then passed them immediately after, this is sleeker
    df = full_clean(data, read_config(protected_cols), f)
    return df

# each tier preloads values into a general cleaning function
def gray_flag(data, f):
    parameters = {
        "strip": False,
        "rename_col": False,
        "rm_tf": False,
        "rm_col": 1,
        "rm_row": 1,
        "rm_dupe_col": False,
        "rm_dupe_row": False,
        "rm_outliers": False,
        "quant_size": 0,
        "protected_cols": None
    }
    full_clean(data, parameters, f)

def green_load(data, f, protected_cols):
    parameters = {
        "strip": True,
        "rename_col": True,
        "rm_tf": True,
        "rm_col": 1,
        "rm_row": 1,
        "rm_dupe_col": False,
        "rm_dupe_row": False,
        "rm_outliers": False,
        "quant_size": 0,
        "protected_cols": protected_cols
    }
    df = full_clean(data, parameters, f)
    return df

def yellow_load(data, f, protected_cols):
    parameters = {
        "strip": True,
        "rename_col": True,
        "rm_tf": True,
        "rm_col": 0.75,
        "rm_row": 1,
        "rm_dupe_col": True,
        "rm_dupe_row": True,
        "rm_outliers": False,
        "quant_size": 0,
        "protected_cols": protected_cols
    }
    df = full_clean(data, parameters, f)
    return df

def orange_load(data, f, protected_cols):
    parameters = {
        "strip": True,
        "rename_col": True,
        "rm_tf": True,
        "rm_col": 0.5,
        "rm_row": 0.75,
        "rm_dupe_col": True,
        "rm_dupe_row": True,
        "rm_outliers": True,
        "quant_size": 0.1,
        "protected_cols": protected_cols
    }
    df = full_clean(data, parameters, f)
    return df

def red_load(data, f, protected_cols):
    parameters = {
        "strip": True,
        "rename_col": True,
        "rm_tf": True,
        "rm_col": 0,
        "rm_row": 0,
        "rm_dupe_col": True,
        "rm_dupe_row": True,
        "rm_outliers": True,
        "quant_size": 0.25,
        "protected_cols": protected_cols
    }
    df = full_clean(data, parameters, f)
    return df

def crimson_clean(data, f, protected_cols, filepath, filename_full):
    # original crimson clean; uncomment to use
    # os.remove(filepath)
    # f.write("\n")
    # f.write(f"Deleted {filename_full}")

    # comment out this crimson clean to use the original
    filename, ext = os.path.splitext(filename_full)

    if protected_cols:
        f.write(f"Protected columns: {protected_cols}\n")
        for col in data.columns:
            if col not in protected_cols:
                data.drop(columns = col, inplace = True)
        data.dropna(how = "all", inplace = True)
        f.write("\nDeleted all non-protected columns and empty rows")
    else:
        data = pd.DataFrame()
        f.write("\nDeleted all columns")

    cleaned_path = FILE_DIR/"data"/"cleaned"/f"{filename}_cleaned{ext}"
    data.to_csv(cleaned_path, index = False)


def begin_clean(filepath, color, protected_cols):
    filename_full = os.path.basename(filepath)
    filename, ext = os.path.splitext(filename_full)

    reports_path = FILE_DIR/"reports"/f"{filename}_logs.txt"
    with open(reports_path, "w") as f:
        f.write(f"Running cleaning level {color} on {filename_full}\n")

        # low_memory=false might be bad here because this is already slow loading big datasets, but it fixed an error with a test dataset
        if ext == ".tsv":
            data = pd.read_csv(filepath, low_memory = False, sep = "\t")
        else:
            data = pd.read_csv(filepath, low_memory = False)

        if color == "Custom":
            output = custom_load(data, f, protected_cols)

        if color == "Gray":
            gray_flag(data, f)
        elif color == "Green":
            output = green_load(data, f, protected_cols)
        elif color == "Yellow":
            output = yellow_load(data, f, protected_cols)
        elif color == "Orange":
            output = orange_load(data, f, protected_cols)
        elif color == "Red":
            output = red_load(data, f, protected_cols)
        elif color == "Crimson":
            crimson_clean(data, f, protected_cols, filepath, filename_full)

        if color != "Gray" and color != "Crimson":
            separator = ","
            if ext == ".tsv":
                separator = "\t"
            cleaned_path = FILE_DIR/"data"/"cleaned"/f"{filename}_cleaned{ext}"
            output.to_csv(cleaned_path, sep = separator, index = False)


# UI section
COLOR_MAP = {
    0: "Gray",
    1: "Green",
    2: "Yellow",
    3: "Orange",
    4: "Red",
    5: "Crimson"
}

image_path = FILE_DIR/"images"
IMAGE_FILES = {
    0: image_path/"gray.png",
    1: image_path/"green.png",
    2: image_path/"yellow.png",
    3: image_path/"orange.png",
    4: image_path/"red.png",
    5: image_path/"crimson.png"
}

class SelectionUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Data Decimator")
        self.root.state("zoomed") 

        # for protected columns
        self.returned_col_set = None

        self.selected_color = COLOR_MAP[0]

        main_frame = tk.Frame(root)
        main_frame.pack(padx = 20, pady = 20)

        # meter display
        self.image_label = tk.Label(main_frame)
        self.image_label.grid(row = 0, column = 0, padx = 20)

        # scale/slider
        self.scale = tk.Scale(
            main_frame,
            from_ = 5,
            to = 0,
            orient = tk.VERTICAL,
            length = 300,
            showvalue = False,
            command = self.on_scale_change
        )
        self.scale.set(2)
        self.scale.grid(row = 0, column = 1, padx = 20)

        # "or" above config options
        self.config_label = tk.Label(
            main_frame,
            text = "Or:",
            font = ("TkDefaultFont", 11)
        )
        self.config_label.grid(row = 0, column = 2, padx = 40, pady = (0, 60))

        # use config button
        self.config_use = tk.Button(
            main_frame,
            text = "Use Config File",
            font = ("TkDefaultFont", 12),
            command = self.use_config
        )
        self.config_use.grid(row = 0, column = 2, padx = 40)

        # edit config button
        self.config_edit = tk.Button(
            main_frame,
            text = "Edit Config File",
            font = ("TkDefaultFont", 12),
            command = self.edit_config
        )
        self.config_edit.grid(row = 0, column = 2, padx = 40, pady = (60, 0))

        # protected columns selector
        self.col_button = tk.Button(
            main_frame,
            text = "Choose Protected Columns (Optional)",
            command = self.select_cols
        )
        self.col_button.grid(row = 0, column = 2, padx = 40, pady = (190, 0))

        # selected color text
        self.color_label = tk.Label(
            root,
            text = f"Selected Level: {self.selected_color}",
            font = ("Arial", 11)
        )
        self.color_label.pack(pady = 10)

        # file selector
        self.file_button = tk.Button(
            root,
            text = "Choose Data",
            command = self.select_file
        )
        self.file_button.pack(pady = 5)

        self.file_label = tk.Label(
            root,
            text = "No file selected",
            anchor = "w",
            font = ("Arial", 13)
            # had to use arial bc the default showed backslashes as the yen symbol
        )
        self.file_label.pack()

        # go button
        self.start_button = tk.Button(
            root,
            text = "GO",
            foreground = "green",
            font = ("TkDefaultFont", 12),
            command = self.start_process,
            width = 20,
            height = 2
        )
        self.start_button.pack(pady = 15)

        # initial image
        self.update_image()

    # records color and calls to change meter image when the slider is moved
    def on_scale_change(self, value):
        value = int(value)
        self.selected_color = COLOR_MAP[value]

        self.color_label.config(
            text = f"Selected Level: {self.selected_color}"
        )

        self.update_image()

    # changes meter image when slider moved
    def update_image(self):
        value = self.scale.get()
        img_filename = IMAGE_FILES[value]

        try:
            self.image = tk.PhotoImage(file = img_filename)
            self.image_label.config(image = self.image)
        except FileNotFoundError:
            self.image_label.config(
                image = "",
                text = f"Missing image:\n{img_filename}"
                # had an issue where images weren't loading bc the cwd was DataDecimator, not src as I assumed
                # this was before adding in pathlib
            )

    # sets the color to custom
    # would love to use update_image here for brevity but that checks the value of the scale
    def use_config(self):
        self.selected_color = "Custom"

        self.color_label.config(
            text = "Selected Level: Custom"
        )

        try:
            off_path = FILE_DIR/"images"/"off.png"
            self.image = tk.PhotoImage(file = off_path)
            self.image_label.config(image = self.image)
        except FileNotFoundError:
            self.image_label.config(
                image = "",
                text = f"Missing image:\nimages/off.png"
            )


    # opens edit config dialog box
    def edit_config(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Edit Config")
        # locks main window until this is closed
        dialog.grab_set()

        # this dialog doesn't need to know the protected columns so just passing None instead of figuring out a way to pass those
        parameters = read_config(None)
        strip = tk.BooleanVar(value = parameters["strip"])
        rename_col = tk.BooleanVar(value = parameters["rename_col"])
        rm_tf = tk.BooleanVar(value = parameters["rm_tf"])
        rm_dupe_col = tk.BooleanVar(value = parameters["rm_dupe_col"])
        rm_dupe_row = tk.BooleanVar(value = parameters["rm_dupe_row"])
        rm_outliers = tk.BooleanVar(value = parameters["rm_outliers"])

        rm_col = tk.StringVar(value = str(parameters["rm_col"]))
        rm_row = tk.StringVar(value = str(parameters["rm_row"]))
        quant_size = tk.StringVar(value = str(parameters["quant_size"]))

        # config dialog frame
        frame = tk.Frame(dialog, padx=15, pady=15)
        frame.pack(fill = "both", expand = True)

        # questions
        row_iterate = 0
        tk.Checkbutton(
            frame,
            text = "Strip whitespace",
            variable = strip
        ).grid(row = row_iterate, column = 0, sticky = "w", pady = 5)
        row_iterate += 1

        tk.Checkbutton(
            frame,
            text = "Normalize column names to snake case",
            variable = rename_col
        ).grid(row = row_iterate, column = 0, sticky = "w", pady = 5)
        row_iterate += 1

        tk.Checkbutton(
            frame,
            text = "Remove columns and rows due to missingness",
            variable = rm_tf
        ).grid(row = row_iterate, column = 0, sticky = "w", pady = 5)
        row_iterate += 1

        tk.Label(
            frame,
            text = "Column missingness threshold to delete (0 to 1):"
        ).grid(row = row_iterate, column = 0, sticky = "w", pady = (10, 2))
        row_iterate += 1

        tk.Entry(
            frame,
            textvariable = rm_col,
            width = 10
        ).grid(row = row_iterate, column = 0, sticky = "w")
        row_iterate += 1

        tk.Label(
            frame,
            text = "Row missingness threshold to delete (0 to 1):"
        ).grid(row = row_iterate, column = 0, sticky = "w", pady = (10, 2))
        row_iterate += 1

        tk.Entry(
            frame,
            textvariable = rm_row,
            width = 10
        ).grid(row = row_iterate, column = 0, sticky = "w")
        row_iterate += 1

        tk.Checkbutton(
            frame,
            text = "Remove duplicate columns",
            variable = rm_dupe_col
        ).grid(row = row_iterate, column = 0, sticky = "w", pady = 5)
        row_iterate += 1

        tk.Checkbutton(
            frame,
            text = "Remove duplicate rows",
            variable = rm_dupe_row
        ).grid(row = row_iterate, column = 0, sticky = "w", pady = 5)
        row_iterate += 1

        tk.Checkbutton(
            frame,
            text = "Remove outliers",
            variable = rm_outliers
        ).grid(row = row_iterate, column = 0, sticky = "w", pady = 5)
        row_iterate += 1

        tk.Label(
            frame,
            text = "Outlier quantile size (0 to 0.5):"
        ).grid(row = row_iterate, column = 0, sticky = "w", pady = (10, 2))
        row_iterate += 1

        tk.Entry(
            frame,
            textvariable = quant_size,
            width = 10
        ).grid(row = row_iterate, column = 0, sticky = "w")
        row_iterate += 1

        # cancel and save buttons
        button_frame = tk.Frame(frame)
        button_frame.grid(row = row_iterate, column = 0, pady = (20, 0), sticky = "e")

        tk.Button(
            button_frame,
            text = "Cancel",
            width = 7,
            command = dialog.destroy
        ).pack(side = "left", padx = 5)

        # it breaks the previous function order but this has to be defined above the button that calls it
        def save_and_close():
            # validate inputs
            try:
                rm_col_val = float(rm_col.get())
                rm_row_val = float(rm_row.get())
                if not (0 <= rm_col_val <= 1) or not (0 <= rm_row_val <= 1):
                    raise ValueError("Missingness removal values must be between 0 and 1")

                mult = float(quant_size.get())
                if not (0 <= mult <= 0.5):
                    raise ValueError("Outlier quantile size must be between 0 and 0.5")

            except ValueError as e:
                messagebox.showerror("Invalid Input", str(e), parent = dialog)
                return

            # send to config
            parameters = {
                "strip": strip.get(),
                "rename_col": rename_col.get(),
                "rm_tf": rm_tf.get(),
                "rm_col": float(rm_col.get()),
                "rm_row": float(rm_row.get()),
                "rm_dupe_col": rm_dupe_col.get(),
                "rm_dupe_row": rm_dupe_row.get(),
                "rm_outliers": rm_outliers.get(),
                "quant_size": float(quant_size.get())
            }

            config_path = FILE_DIR/"config"/"config.json"
            with open(config_path, "w") as f:
                json.dump(parameters, f, indent = 4)

            dialog.destroy()

        tk.Button(
            button_frame,
            text = "Save",
            width = 7,
            command = save_and_close
        ).pack(side = "left", padx = 5)


    # opens the file system and shows .csv and .tsv files, which can be selected
    def select_file(self):
        data_filename = filedialog.askopenfilename(
            title="Select Data",
            initialdir = FILE_DIR,
            filetypes = [
                ("CSV files", "*.csv"),
                ("TSV files", "*.tsv"),
            ]
        )

        if data_filename:
            self.data_filename = data_filename
            self.file_label.config(
                text=f"Selected: {os.path.relpath(data_filename)}"
            )


    # opens a list of columns to be selected for protection
    def select_cols(self):
        try:
            self.data_filename
        except AttributeError:
            messagebox.showerror("Invalid Input", "No data file was selected")
            return

        protected_cols = set()

        col_dialog = tk.Toplevel(self.root)
        col_dialog.title("Select Protected Columns")
        col_dialog.geometry("400x500")
        col_dialog.grab_set()

        # width chosen arbitrarily, it seems like it'll fit most column names
        # without specifying here the width was set way too wide
        col_canvas = tk.Canvas(col_dialog, width = 250)
        scrollbar = tk.Scrollbar(
            col_dialog,
            command = col_canvas.yview
        )
        col_canvas.configure(yscrollcommand = scrollbar.set)

        col_canvas.pack(side = "left", fill = "both", expand = True)
        scrollbar.pack(side = "right", fill = "y", padx = (0, 10))

        col_frame = tk.Frame(col_canvas)

        col_canvas.create_window(
            (0, 0),
            anchor = "nw",
            window = col_frame
        )

        col_vars = {}

        def create_boxes():
            col_names = pd.read_csv(self.data_filename, nrows = 0).columns

            for col in col_names:
                var = tk.BooleanVar(value = col in self.returned_col_set if self.returned_col_set is not None else False)
                col_vars[col] = var

                box = tk.Checkbutton(
                    col_frame,
                    text = str(col),
                    variable = var,
                    command = lambda tog_col = col, tog_var = var: toggle_col(tog_col, tog_var)
                )
                box.pack(anchor = "w", padx = 5, pady = 2)

            col_frame.update_idletasks()
            col_canvas.configure(scrollregion = col_canvas.bbox("all"))

        def toggle_col(col, var):
            if var.get():
                protected_cols.add(col)
            else:
                protected_cols.discard(col)

        # cancel and save buttons
        button_frame = tk.Frame(col_dialog)
        button_frame.pack(side = "right", pady = 20)

        tk.Button(
            button_frame,
            text = "Cancel",
            width = 7,
            command = col_dialog.destroy
        ).pack(pady = 2)

        def save_and_close_cols():
            if len(protected_cols) != 0:
                self.returned_col_set = protected_cols

            col_dialog.destroy()

        tk.Button(
            button_frame,
            text = "Save",
            width = 7,
            command = save_and_close_cols
        ).pack(pady = 2)

        create_boxes()

    def start_process(self):
        if self.selected_color == "Crimson":
            if not messagebox.askyesno("Crimson Alert", "Are you sure you want to use crimson cleaning?"):
                return

        data_path_obj = Path(self.data_filename)
        if data_path_obj.stat().st_size == 0:
            messagebox.showerror("Invalid File", "The provided file is empty")
            return

        try:
            begin_clean(self.data_filename, self.selected_color, self.returned_col_set)
        except AttributeError:
            messagebox.showerror("Invalid Input", "No data file was selected")
            return

        root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    window = SelectionUI(root)
    root.mainloop()