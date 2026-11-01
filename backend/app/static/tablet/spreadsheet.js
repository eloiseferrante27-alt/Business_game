(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.GMixSpreadsheet = api;
}(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const FUNCTIONS = new Set(["SOMME", "MOYENNE", "MIN", "MAX", "SI"]);

  function columnName(index) {
    let name = "";
    let value = index + 1;
    while (value > 0) {
      name = String.fromCharCode(65 + ((value - 1) % 26)) + name;
      value = Math.floor((value - 1) / 26);
    }
    return name;
  }

  function cellReference(reference) {
    const match = /^([A-Z]+)([1-9][0-9]*)$/.exec(reference.toUpperCase());
    if (!match) return null;
    let column = 0;
    for (const letter of match[1]) column = column * 26 + letter.charCodeAt(0) - 64;
    return { row: Number(match[2]) - 1, column: column - 1 };
  }

  function numeric(value) {
    if (typeof value === "number") return Number.isFinite(value) ? value : NaN;
    if (typeof value !== "string" || value.trim() === "") return NaN;
    const parsed = Number(value.trim().replace(/\s/g, "").replace(",", "."));
    return Number.isFinite(parsed) ? parsed : NaN;
  }

  function createGrid(rows, columns, values) {
    return Array.from({ length: rows }, (_, row) => Array.from({ length: columns }, (_, column) => {
      return values && values[row] && values[row][column] !== undefined ? values[row][column] : "";
    }));
  }

  function tokenize(source) {
    const tokens = [];
    let index = 0;
    while (index < source.length) {
      const rest = source.slice(index);
      const space = /^\s+/.exec(rest);
      if (space) { index += space[0].length; continue; }
      const number = /^(?:\d+(?:[.,]\d+)?|[.,]\d+)/.exec(rest);
      if (number) {
        tokens.push({ type: "number", value: Number(number[0].replace(",", ".")) });
        index += number[0].length;
        continue;
      }
      const string = /^"(?:[^"]|"")*"/.exec(rest);
      if (string) {
        tokens.push({ type: "string", value: string[0].slice(1, -1).replace(/""/g, '"') });
        index += string[0].length;
        continue;
      }
      const identifier = /^[A-Za-zÀ-ÖØ-öø-ÿ_][A-Za-zÀ-ÖØ-öø-ÿ_0-9]*/.exec(rest);
      if (identifier) {
        tokens.push({ type: "identifier", value: identifier[0].toUpperCase() });
        index += identifier[0].length;
        continue;
      }
      const operator = /^(?:>=|<=|<>|[+\-*/^()=:;,><])/.exec(rest);
      if (operator) {
        tokens.push({ type: operator[0], value: operator[0] });
        index += operator[0].length;
        continue;
      }
      throw new Error("Formule illisible");
    }
    tokens.push({ type: "eof", value: "" });
    return tokens;
  }

  function evaluateFormula(source, grid, stack) {
    const tokens = tokenize(source);
    let cursor = 0;

    function peek(type) { return tokens[cursor].type === type; }
    function take(type) {
      if (!peek(type)) throw new Error("Formule incomplète");
      return tokens[cursor++];
    }

    function scalar(value) {
      if (Array.isArray(value)) {
        if (value.length !== 1) throw new Error("Une cellule est attendue");
        return scalar(value[0]);
      }
      return value;
    }

    function numberValue(value) {
      if (value === "" || value === null || value === undefined || value === false) return 0;
      if (value === true) return 1;
      const parsed = numeric(value);
      if (Number.isNaN(parsed)) throw new Error("Nombre attendu");
      return parsed;
    }

    function resolveCell(reference) {
      const address = cellReference(reference);
      if (!address) throw new Error("Référence inconnue");
      return readCell(address.row, address.column, grid, stack || new Set());
    }

    function resolveRange(start, end) {
      const first = cellReference(start);
      const last = cellReference(end);
      if (!first || !last) throw new Error("Plage inconnue");
      const values = [];
      for (let row = Math.min(first.row, last.row); row <= Math.max(first.row, last.row); row += 1) {
        for (let column = Math.min(first.column, last.column); column <= Math.max(first.column, last.column); column += 1) {
          values.push(readCell(row, column, grid, stack || new Set()));
        }
      }
      return values;
    }

    function primary() {
      if (peek("number") || peek("string")) return tokens[cursor++].value;
      if (peek("identifier")) {
        const identifier = tokens[cursor++].value;
        if (peek("(")) {
          if (!FUNCTIONS.has(identifier)) throw new Error("Fonction non autorisée");
          take("(");
          const args = [];
          if (!peek(")")) {
            do { args.push(expression()); } while (peek(";") && tokens[cursor++] && true);
          }
          take(")");
          return applyFunction(identifier, args);
        }
        if (identifier === "VRAI") return true;
        if (identifier === "FAUX") return false;
        if (peek(":")) {
          take(":");
          return resolveRange(identifier, take("identifier").value);
        }
        return resolveCell(identifier);
      }
      if (peek("(")) {
        take("(");
        const value = expression();
        take(")");
        return value;
      }
      throw new Error("Valeur attendue");
    }

    function unary() {
      if (peek("+") || peek("-")) {
        const operator = tokens[cursor++].type;
        const value = numberValue(scalar(unary()));
        return operator === "-" ? -value : value;
      }
      return primary();
    }

    function power() {
      let left = unary();
      if (peek("^")) {
        take("^");
        left = Math.pow(numberValue(scalar(left)), numberValue(scalar(power())));
      }
      return left;
    }

    function multiplication() {
      let left = power();
      while (peek("*") || peek("/")) {
        const operator = tokens[cursor++].type;
        const right = power();
        if (operator === "/" && numberValue(scalar(right)) === 0) throw new Error("Division par zéro");
        left = operator === "*" ? numberValue(scalar(left)) * numberValue(scalar(right)) : numberValue(scalar(left)) / numberValue(scalar(right));
      }
      return left;
    }

    function addition() {
      let left = multiplication();
      while (peek("+") || peek("-")) {
        const operator = tokens[cursor++].type;
        const right = multiplication();
        left = operator === "+" ? numberValue(scalar(left)) + numberValue(scalar(right)) : numberValue(scalar(left)) - numberValue(scalar(right));
      }
      return left;
    }

    function comparison() {
      let left = addition();
      if (peek("=") || peek(">") || peek("<") || peek(">=") || peek("<=") || peek("<>")) {
        const operator = tokens[cursor++].type;
        const right = addition();
        const a = scalar(left);
        const b = scalar(right);
        if (operator === "=") return a === b || String(a) === String(b);
        if (operator === "<>") return !(a === b || String(a) === String(b));
        const first = numeric(a);
        const second = numeric(b);
        const x = Number.isNaN(first) || Number.isNaN(second) ? String(a) : first;
        const y = Number.isNaN(first) || Number.isNaN(second) ? String(b) : second;
        if (operator === ">") return x > y;
        if (operator === "<") return x < y;
        if (operator === ">=") return x >= y;
        return x <= y;
      }
      return left;
    }

    function expression() { return comparison(); }
    const result = expression();
    take("eof");
    return result;
  }

  function flatten(values) {
    return values.reduce((all, value) => all.concat(Array.isArray(value) ? flatten(value) : value), []);
  }

  function applyFunction(name, args) {
    if (name === "SI") {
      if (args.length !== 3) throw new Error("SI attend trois arguments");
      if (Array.isArray(args[0]) && args[0].length !== 1) throw new Error("Une condition est attendue");
      const condition = Array.isArray(args[0]) ? args[0][0] : args[0];
      return condition ? args[1] : args[2];
    }
    const numbers = flatten(args).map(numeric).filter((value) => !Number.isNaN(value));
    if (!numbers.length && name !== "SOMME") throw new Error("Plage vide");
    if (name === "SOMME") return numbers.reduce((sum, value) => sum + value, 0);
    if (name === "MOYENNE") return numbers.reduce((sum, value) => sum + value, 0) / numbers.length;
    if (name === "MIN") return Math.min(...numbers);
    return Math.max(...numbers);
  }

  function readCell(row, column, grid, stack) {
    if (row < 0 || column < 0 || !grid[row] || grid[row][column] === undefined) return "";
    const raw = grid[row][column];
    if (typeof raw !== "string" || !raw.trim().startsWith("=")) return raw;
    const key = `${row}:${column}`;
    if (stack.has(key)) throw new Error("Référence circulaire");
    const nextStack = new Set(stack);
    nextStack.add(key);
    return evaluateFormula(raw.trim().slice(1), grid, nextStack);
  }

  function evaluate(value, grid) {
    try {
      if (typeof value !== "string" || !value.trim().startsWith("=")) return value;
      const result = evaluateFormula(value.trim().slice(1), grid || [], new Set());
      return typeof result === "number" && !Number.isFinite(result) ? "#ERREUR" : result;
    } catch (error) {
      return error.message === "Référence circulaire" ? "#CIRC" : "#ERREUR";
    }
  }

  function csvCell(value) {
    let text = value === null || value === undefined ? "" : String(value);
    if (/^[=+\-@]/.test(text)) text = `'${text}`;
    return /[";\n\r]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
  }

  function toCsv(grid) {
    return grid.map((row, rowIndex) => row.map((value, columnIndex) => {
      const result = typeof value === "string" && value.trim().startsWith("=") ? evaluate(value, grid) : value;
      return csvCell(result);
    }).join(";")).join("\r\n");
  }

  return { columnName, createGrid, evaluate, toCsv };
}));
