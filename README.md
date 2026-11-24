# Data Decimator Full Release
by cwmullens  

A .csv and .tsv cleaning UI, with several presets and allowing for custom configurations. Originally created for a class but now cleaned up and given additional functionality.

## Description
To use, run main.py, which accesses the UI. In the UI window, move the slider up or down to select a cleaning preset, or press the Use Config File button to use the config file, which can also be edited by using the Edit Config File button and the resulting dialog box. Additionally, columns that need to be kept that otherwise wouldn't be can be specified in the Protected Columns dialog box.  
Then, the preferred dataset can be selected using the Choose Data button, opening the file explorer and allowing for a .csv or .tsv file to be selected. To streamline the process it is recommended to place datasets into the data/raw/ directory.  
After making sure everything is correct, press the GO button to run the selected processes on the dataset. Depending on the size of the file, this process may take a little while. After this, the UI window will close, indicating the cleaning is done. The outputted data can be found in data/cleaned/, and the logs from the cleaning can be found in the reports/ directory.  

The preset cleaning options are: 
- Gray- simply flags the data
- Green- light cleaning with removing whitespace, removing fully empty rows and columns, and normalizing column names into snake case
- Yellow- like previous level but now removes columns that are 75% empty and dropping any columns and rows that are duplicates
- Orange- building on Yellow but now removing 50% empty columns, 75% empty rows, and removing outliers with a quantile size of 0.1
- Red- the final real level, just like Orange but now removing any rows with any missing values after dropping all empty columns and changing the outlier quantile size to 0.25
- Crimson- scrubbing the data fully

Each level is meant to build upon the last while trading preservation for quality or consistency. The specifics of the processes are explained below, written as they are in the editing config dialog box: 
- Strip whitespace: removes leading and trailing spaces in column names and in each string cell
- Normalize column names: attempts to shift column names to snake case
- Remove columns and rows due to missingness: the check for if any rows and columns should be removed due to missing values; the following two only apply if this is true
- Column missingness threshold to delete (0 to 1): percentage of missing values in a column that needs to be crossed for the column to be deleted
- Row missingness threshold to delete (0 to 1): percentage of missing values in a row that needs to be crossed for the row to be deleted (set to 0 to remove rows with any missing values)
- Remove duplicate columns: removes duplicate columns while keeping the original
- Remove duplicate rows: removes duplicate rows while keeping the original
- Remove outliers: uses the IQR outlier formula to identify and remove potential outliers
- Outlier quantile size (0 to 0.5): the size of each quantile in the outlier formula; the lower the number, the less data identified as outliers

A sample fictional dataset is included, along with the associated cleaned version (with the yellow preset) and log report.  

## Dependencies
Ensure all dependencies are installed. These libraries are 
- *pandas*
- *os*
- *tkinter*
- *json*
- *pathlib*  

Luckily, *os*, *tkinter*, *json*, and *pathlib* are part of the modern Python standard library, but *pandas* must be installed, such as by running the code below.  

```pip install pandas```  

For additional information, this program was built using Python version **3.14.6**.  

## Limitations
- There are no imputations. The cleaning function just removes things.
- If the same dataset is used, even with different presets, the former outputted data and log file are overwritten.
- config.json has a default copy, which can be used for resetting the values, either by making a copy of the default and renaming it or just copying the contents directly to config.json.
- The Use Config File button must still be clicked after editing the config file.
- To not use the custom config after pressing the button to use it, simply move the slider on the presets.
- Importantly, protected columns are not saved to config. They must be selected every time the data is cleaned.
- Protected columns are protected by name, which means that if two columns have the same name they will both be protected.
- Protected columns will have their names normalized and whitespace removed if the options are selected.
- The snake case algorithm isn't foolproof, it uses several heuristics but cannot be perfect. For example, a test dataset had the column name SPSOnly, which should obviously become sps_only, but the algorithm has no way of knowing where to split, and working around this case just added worse ones.
- The outlier algorithm is harsh, it removes an entire row if at least one value in it is an outlier in one column.
- The accepted way to change how strict the IQR outlier formula is is by changing the constant the IQR is multiplied by. 3 is meant to be extremely strict, but testing showed it would remove columns the current system doesn't when the quantile size is set to 0.1.
- To counteract how harsh it is, the outlier removal will not work if the remaining data has less than 50% of the original rows.
