import nbformat

def write_value_to_file(notebook_path, site_obj_str, new_value):
    """
    writes the random site value to the 1st code cell in topology_variables.ipynb
    """
    nb = nbformat.read(notebook_path, as_version=4)
    for cell in nb.cells:
        if cell.cell_type == 'code':
            updated_source = []
            for line in cell.source.splitlines():
                if (site_obj_str+'=') in line or (site_obj_str+' =') in line:
                    updated_source.append(f'{site_obj_str} = "{new_value}"')
                else:
                    updated_source.append(line)
            cell.source = "\n".join(updated_source)
            break  # Stop after updating the first code cell
    
    # Write the notebook back to the file
    nbformat.write(nb, notebook_path)
