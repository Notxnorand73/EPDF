#!/usr/bin/env python3
import sys

class EPDF:
    def __init__(self):
        self.variables = {}
        self.lists = {}
        self.maps = {}
        self.files = {}

    def eval_value(self, val):
        val = val.strip()
        if val in self.variables:
            return self.variables[val]
        if val in self.lists:
            return self.lists[val]
        if val in self.maps:
            return self.maps[val]
        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
            return val[1:-1]
        try:
            return eval(val, {}, self.variables)
        except (NameError, SyntaxError):
            return val.strip('"\'')  # fallback

    def collect_block(self, lines, start_index):
        block = []
        i = start_index
        while i < len(lines):
            line = lines[i].strip()
            if line == '}':
                return block, i - start_index + 1
            block.append(lines[i])
            i += 1
        return block, i - start_index

    def execute(self, code_lines):
        lines = code_lines.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line or line.startswith('#'):
                i += 1
                continue

            # -------------------------------------------------------------
            # TRY / EXCEPT / FINALLY
            # -------------------------------------------------------------
            if line.startswith('try'):
                try_block, offset = self.collect_block(lines, i + 1)
                i += offset
                j = i
                except_block, except_var, finally_block = [], None, []

                while j < len(lines):
                    next_line = lines[j].strip()
                    if next_line.startswith('except as '):
                        except_var = next_line[10:].strip().rstrip('{').strip()
                        except_block, ex_offset = self.collect_block(lines, j + 1)
                        j += ex_offset
                    elif next_line.startswith('except'):
                        except_block, ex_offset = self.collect_block(lines, j + 1)
                        j += ex_offset
                    elif next_line.startswith('finally'):
                        finally_block, fin_offset = self.collect_block(lines, j + 1)
                        j += fin_offset
                    else:
                        break

                try:
                    self.execute('\n'.join(try_block))
                except Exception as e:
                    if except_var:
                        self.variables[except_var] = e
                    if except_block:
                        self.execute('\n'.join(except_block))
                finally:
                    if finally_block:
                        self.execute('\n'.join(finally_block))
                i = j
                continue

            # -------------------------------------------------------------
            # SIMPLE INDEXING ASSIGNMENT  (mylist[2] = value)
            # -------------------------------------------------------------
            if '[' in line and ']' in line and '=' in line:
                left, right = line.split('=', 1)
                left = left.strip()
                right = right.strip()

                if left.endswith(']') and '[' in left:
                    name, idx = left.split('[', 1)
                    name = name.strip()
                    idx = idx[:-1].strip()

                    idx_val = self.eval_value(idx)
                    val_val = self.eval_value(right)

                    # list indexing
                    if name in self.lists:
                        self.lists[name][idx_val] = val_val
                        i += 1
                        continue

                    # map indexing
                    if name in self.maps:
                        self.maps[name][idx_val] = val_val
                        i += 1
                        continue

                    # variable containing list/dict
                    if name in self.variables and isinstance(self.variables[name], (list, dict)):
                        self.variables[name][idx_val] = val_val
                        i += 1
                        continue

            # -------------------------------------------------------------
            # VARIABLE ASSIGNMENT
            # -------------------------------------------------------------
            if '=' in line and not line.startswith(('if', 'for', 'while', 'open')):
                var, val = map(str.strip, line.split('=', 1))

                # f.readlines()
                if '.readlines()' in val:
                    obj_name = val.split('.')[0]
                    if obj_name in self.files:
                        self.variables[var] = self.files[obj_name].readlines()
                    i += 1
                    continue

                # map[key] = value
                if '[' in var and ']' in var:
                    map_name = var[:var.index('[')].strip()
                    key = var[var.index('[')+1 : var.index(']')].strip()
                    if map_name not in self.maps:
                        self.maps[map_name] = {}
                    self.maps[map_name][self.eval_value(key)] = self.eval_value(val)
                    i += 1
                    continue

                # list literal
                if val.startswith('[') and val.endswith(']'):
                    self.lists[var] = eval(val, {}, self.variables)
                # map literal
                elif val.startswith('{') and val.endswith('}'):
                    self.maps[var] = eval(val, {}, self.variables)
                else:
                    self.variables[var] = self.eval_value(val)

                i += 1
                continue

            # -------------------------------------------------------------
            # PRINT
            # -------------------------------------------------------------
            if line.startswith('print(') and line.endswith(')'):
                expr = line[6:-1].strip()

                if '[' in expr and ']' in expr:
                    map_name = expr[:expr.index('[')].strip()
                    key = expr[expr.index('[')+1 : expr.index(']')].strip()
                    if map_name in self.maps:
                        print(self.maps[map_name].get(self.eval_value(key)))
                        i += 1
                        continue

                try:
                    value = eval(expr, {}, self.variables)
                except (NameError, SyntaxError):
                    value = self.eval_value(expr)

                print(value)
                i += 1
                continue

            # -------------------------------------------------------------
            # LIST & MAP METHODS
            # -------------------------------------------------------------
            if '.' in line:
                obj, rest = line.split('.', 1)
                obj = obj.strip()
                rest = rest.strip()

                # -- LIST METHODS --
                if obj in self.lists:
                    if rest.startswith('append('):
                        self.lists[obj].append(self.eval_value(rest[7:-1]))
                    elif rest.startswith('pop()'):
                        self.lists[obj].pop()
                    elif rest.startswith('remove('):
                        self.lists[obj].remove(self.eval_value(rest[7:-1]))
                    elif rest.startswith('inject('):
                        val_idx = rest[7:-1]
                        if ',' in val_idx:
                            val, idx = val_idx.split(',', 1)
                            self.lists[obj].insert(int(self.eval_value(idx.strip())), self.eval_value(val.strip()))
                        else:
                            self.lists[obj].append(self.eval_value(val_idx))
                    elif rest.startswith('wash('):
                        val = rest[5:-1]
                        self.lists[obj] = [x for x in self.lists[obj] if x != self.eval_value(val)]
                    elif rest.startswith('length()'):
                        print(len(self.lists[obj]))
                    elif rest.startswith('index('):
                        print(self.lists[obj].index(self.eval_value(rest[6:-1])))
                    elif rest.startswith('filter('):
                        val = self.eval_value(rest[7:-1])
                        print([x for x in self.lists[obj] if x == val])
                    elif rest.startswith('sieve('):
                        val = str(self.eval_value(rest[6:-1])).lower()
                        print([x for x in self.lists[obj] if str(x).lower() == val])
                    i += 1
                    continue

                # -- MAP METHODS --
                if obj in self.maps:
                    if rest.startswith('keys()'):
                        print(list(self.maps[obj].keys()))
                    elif rest.startswith('values()'):
                        print(list(self.maps[obj].values()))
                    elif rest.startswith('filter('):
                        val = self.eval_value(rest[7:-1])
                        filtered = {k:v for k,v in self.maps[obj].items() if v == val}
                        print(filtered)
                    i += 1
                    continue

            # -------------------------------------------------------------
            # CONDITIONALS
            # -------------------------------------------------------------
            if line.startswith('if '):
                cond = line[3:].strip().rstrip('{').strip()
                block, offset = self.collect_block(lines, i + 1)
                if eval(cond, {}, self.variables):
                    self.execute('\n'.join(block))
                i += offset
                continue

            if line.startswith('elif '):
                cond = line[5:].strip().rstrip('{').strip()
                block, offset = self.collect_block(lines, i + 1)
                if eval(cond, {}, self.variables):
                    self.execute('\n'.join(block))
                i += offset
                continue

            if line.startswith('else'):
                block, offset = self.collect_block(lines, i + 1)
                self.execute('\n'.join(block))
                i += offset
                continue

            # -------------------------------------------------------------
            # LOOPS
            # -------------------------------------------------------------
            if line.startswith('for '):
                parts = line[4:].strip().rstrip('{').split('in')
                var = parts[0].strip()
                iterable = parts[1].strip()

                # handle list.length()
                if iterable.endswith('.length()') and '.' in iterable:
                    list_name = iterable[:iterable.index('.')]
                    if list_name in self.lists:
                        length = len(self.lists[list_name])
                    else:
                        raise ValueError(f"Unknown list {list_name} in for loop")
                else:
                    length = int(self.eval_value(iterable))

                block, offset = self.collect_block(lines, i + 1)
                for j in range(length):
                    self.variables[var] = j
                    self.execute('\n'.join(block))
                i += offset
                continue

            if line.startswith('while '):
                cond = line[6:].strip().rstrip('{').strip()
                block, offset = self.collect_block(lines, i + 1)
                while eval(cond, {}, self.variables):
                    self.execute('\n'.join(block))
                i += offset
                continue

            # -------------------------------------------------------------
            # FILE OPEN
            # -------------------------------------------------------------
            if line.startswith('open(') and 'as' in line:
                path = line[5:line.index(')')].strip()
                if (path.startswith('"') and path.endswith('"')) or (path.startswith("'") and path.endswith("'")):
                    path = path[1:-1]

                var_name = line[line.index('as')+2:].strip().rstrip('{').strip()

                block, offset = self.collect_block(lines, i + 1)
                with open(path, 'r') as f:
                    self.files[var_name] = f
                    self.variables[var_name] = f
                    self.execute('\n'.join(block))
                    del self.files[var_name]

                i += offset
                continue

            i += 1

# =====================================================================
# REPL & FILE EXECUTION
# =====================================================================

def repl():
    epdf = EPDF()
    print("EPDF REPL. Type 'exit' to quit.")
    buffer = ""

    while True:
        try:
            line = input(">>> ").rstrip()
        except EOFError:
            break

        if line == "exit":
            break

        buffer += line + "\n"

        if line.endswith('}') or line == '}':
            try:
                epdf.execute(buffer)
            except Exception as e:
                print("Error:", e)
            buffer = ""

def run_file(path):
    epdf = EPDF()
    with open(path, 'r') as f:
        code = f.read()
    epdf.execute(code)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_file(sys.argv[1])
    else:
        repl()
