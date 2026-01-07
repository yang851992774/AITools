<template>
  <div class="calculator">
    <div class="calculator-container">
      <div class="display">
        <div class="expression">{{ expression || '0' }}</div>
        <div class="result">{{ result || '0' }}</div>
      </div>
      
      <div class="buttons">
        <!-- 第一行：科学函数 -->
        <button @click="handleFunction('sin')" class="btn function">sin</button>
        <button @click="handleFunction('cos')" class="btn function">cos</button>
        <button @click="handleFunction('tan')" class="btn function">tan</button>
        <button @click="handleFunction('log')" class="btn function">log</button>
        <button @click="handleFunction('ln')" class="btn function">ln</button>
        
        <!-- 第二行：更多科学函数 -->
        <button @click="handleFunction('sqrt')" class="btn function">√</button>
        <button @click="handleFunction('pow')" class="btn function">x^y</button>
        <button @click="handleFunction('exp')" class="btn function">e^x</button>
        <button @click="handleFunction('pi')" class="btn function">π</button>
        <button @click="handleFunction('e')" class="btn function">e</button>
        
        <!-- 第三行：清除和括号 -->
        <button @click="clear" class="btn clear">C</button>
        <button @click="clearEntry" class="btn clear">CE</button>
        <button @click="backspace" class="btn clear">⌫</button>
        <button @click="append('(')" class="btn operator">(</button>
        <button @click="append(')')" class="btn operator">)</button>
        
        <!-- 第四行：数字和运算符 -->
        <button @click="append('7')" class="btn number">7</button>
        <button @click="append('8')" class="btn number">8</button>
        <button @click="append('9')" class="btn number">9</button>
        <button @click="append('/')" class="btn operator">÷</button>
        <button @click="handleFunction('factorial')" class="btn function">n!</button>
        
        <!-- 第五行 -->
        <button @click="append('4')" class="btn number">4</button>
        <button @click="append('5')" class="btn number">5</button>
        <button @click="append('6')" class="btn number">6</button>
        <button @click="append('*')" class="btn operator">×</button>
        <button @click="handleFunction('percent')" class="btn function">%</button>
        
        <!-- 第六行 -->
        <button @click="append('1')" class="btn number">1</button>
        <button @click="append('2')" class="btn number">2</button>
        <button @click="append('3')" class="btn number">3</button>
        <button @click="append('-')" class="btn operator">−</button>
        <button @click="handleFunction('1/x')" class="btn function">1/x</button>
        
        <!-- 第七行 -->
        <button @click="append('0')" class="btn number zero">0</button>
        <button @click="append('.')" class="btn number">.</button>
        <button @click="calculate" class="btn operator equals">=</button>
        <button @click="append('+')" class="btn operator">+</button>
        <button @click="handleFunction('square')" class="btn function">x²</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const expression = ref('')
const result = ref('')

const append = (value) => {
  if (expression.value === '0' && value !== '.') {
    expression.value = value
  } else {
    expression.value += value
  }
  calculate()
}

const handleFunction = (func) => {
  const currentValue = result.value || expression.value || '0'
  let newExpression = ''
  
  switch (func) {
    case 'sin':
      newExpression = `Math.sin(${currentValue})`
      break
    case 'cos':
      newExpression = `Math.cos(${currentValue})`
      break
    case 'tan':
      newExpression = `Math.tan(${currentValue})`
      break
    case 'log':
      newExpression = `Math.log10(${currentValue})`
      break
    case 'ln':
      newExpression = `Math.log(${currentValue})`
      break
    case 'sqrt':
      newExpression = `Math.sqrt(${currentValue})`
      break
    case 'exp':
      newExpression = `Math.exp(${currentValue})`
      break
    case 'pi':
      newExpression = 'Math.PI'
      break
    case 'e':
      newExpression = 'Math.E'
      break
    case 'square':
      newExpression = `Math.pow(${currentValue}, 2)`
      break
    case 'factorial':
      const num = parseFloat(currentValue)
      if (num >= 0 && num <= 170 && Number.isInteger(num)) {
        let fact = 1
        for (let i = 2; i <= num; i++) {
          fact *= i
        }
        newExpression = fact.toString()
      } else {
        result.value = 'Error'
        return
      }
      break
    case 'percent':
      newExpression = `(${currentValue}) / 100`
      break
    case '1/x':
      newExpression = `1 / (${currentValue})`
      break
    case 'pow':
      newExpression = `Math.pow(${currentValue}, `
      break
  }
  
  if (func === 'pow') {
    expression.value = newExpression
  } else {
    try {
      const evalResult = safeEval(newExpression)
      if (evalResult !== null && evalResult !== undefined && !isNaN(evalResult)) {
        expression.value = evalResult.toString()
        result.value = evalResult.toString()
      } else {
        result.value = 'Error'
      }
    } catch (error) {
      result.value = 'Error'
    }
  }
}

const safeEval = (expr) => {
  try {
    // 替换数学函数和常量
    expr = expr
      .replace(/Math\.sin/g, 'Math.sin')
      .replace(/Math\.cos/g, 'Math.cos')
      .replace(/Math\.tan/g, 'Math.tan')
      .replace(/Math\.log10/g, 'Math.log10')
      .replace(/Math\.log/g, 'Math.log')
      .replace(/Math\.sqrt/g, 'Math.sqrt')
      .replace(/Math\.pow/g, 'Math.pow')
      .replace(/Math\.exp/g, 'Math.exp')
      .replace(/Math\.PI/g, Math.PI.toString())
      .replace(/Math\.E/g, Math.E.toString())
      .replace(/×/g, '*')
      .replace(/÷/g, '/')
      .replace(/−/g, '-')
    
    // 使用 Function 构造函数来安全地计算表达式
    return new Function('Math', `return ${expr}`)(Math)
  } catch (error) {
    return null
  }
}

const calculate = () => {
  if (!expression.value) {
    result.value = '0'
    return
  }
  
  try {
    const evalResult = safeEval(expression.value)
    if (evalResult !== null && evalResult !== undefined && !isNaN(evalResult)) {
      // 格式化结果，避免过长的小数
      if (Math.abs(evalResult) < 1e-10) {
        result.value = '0'
      } else if (Math.abs(evalResult) > 1e10) {
        result.value = evalResult.toExponential(6)
      } else {
        // 限制小数位数
        const rounded = Math.round(evalResult * 1e10) / 1e10
        result.value = rounded.toString()
      }
    } else {
      result.value = 'Error'
    }
  } catch (error) {
    result.value = 'Error'
  }
}

const clear = () => {
  expression.value = ''
  result.value = ''
}

const clearEntry = () => {
  expression.value = ''
  result.value = '0'
}

const backspace = () => {
  if (expression.value.length > 0) {
    expression.value = expression.value.slice(0, -1)
    calculate()
  }
}
</script>

<style scoped>
.calculator {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: #000000;
  padding: 20px;
}

.calculator-container {
  background: #000000;
  border-radius: 0;
  padding: 20px;
  max-width: 500px;
  width: 100%;
}

.display {
  background: #000000;
  border-radius: 0;
  padding: 30px 20px;
  margin-bottom: 20px;
  min-height: 120px;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
}

.expression {
  color: rgba(255, 255, 255, 0.5);
  font-size: 20px;
  text-align: right;
  margin-bottom: 10px;
  min-height: 25px;
  word-break: break-all;
  font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Helvetica Neue', Arial, sans-serif;
}

.result {
  color: #ffffff;
  font-size: 64px;
  font-weight: 300;
  text-align: right;
  word-break: break-all;
  font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Helvetica Neue', Arial, sans-serif;
  line-height: 1.1;
}

.buttons {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
}

.btn {
  border: none;
  border-radius: 50%;
  padding: 0;
  aspect-ratio: 1;
  font-size: 32px;
  font-weight: 400;
  cursor: pointer;
  transition: all 0.1s ease;
  background: #505050;
  color: #ffffff;
  font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Helvetica Neue', Arial, sans-serif;
  display: flex;
  align-items: center;
  justify-content: center;
  user-select: none;
  -webkit-tap-highlight-color: transparent;
}

.btn:active {
  transform: scale(0.95);
  opacity: 0.8;
}

.btn.number {
  background: #505050;
  color: #ffffff;
}

.btn.number:active {
  background: #6d6d6d;
}

.btn.operator {
  background: #ff9500;
  color: #ffffff;
}

.btn.operator:active {
  background: #ffad33;
}

.btn.clear {
  background: #d4d4d2;
  color: #000000;
  font-weight: 500;
}

.btn.clear:active {
  background: #ffffff;
}

.btn.function {
  background: #505050;
  color: #ffffff;
  font-size: 20px;
  font-weight: 400;
}

.btn.function:active {
  background: #6d6d6d;
}

.btn.equals {
  background: #ff9500;
  color: #ffffff;
}

.btn.equals:active {
  background: #ffad33;
}

.btn.zero {
  grid-column: span 1;
  border-radius: 50%;
}

@media (max-width: 600px) {
  .calculator-container {
    padding: 15px;
  }
  
  .display {
    padding: 20px 15px;
    min-height: 100px;
  }
  
  .result {
    font-size: 48px;
  }
  
  .expression {
    font-size: 18px;
  }
  
  .btn {
    font-size: 28px;
  }
  
  .btn.function {
    font-size: 20px;
  }
  
  .buttons {
    gap: 10px;
  }
}
</style>
