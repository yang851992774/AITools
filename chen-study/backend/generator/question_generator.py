"""
数学题目生成器
"""
import random
from typing import List, Dict, Tuple


class QuestionGenerator:
    """生成小学数学题目"""
    
    def __init__(self, max_value: int, difficulty: int = 50):
        """
        初始化生成器
        :param max_value: 最大数值（M）
        :param difficulty: 难度值（1-100），默认50
        """
        self.max_value = max_value
        self.difficulty = max(1, min(100, difficulty))  # 确保在1-100范围内
    
    def _get_min_value(self, base_min: int = 1) -> int:
        """
        根据难度计算最小数值
        难度越高，最小数值越大，避免生成1+2这种太简单的题目
        """
        # 难度1-100映射到最小数值
        # 难度1: 最小值为1
        # 难度50: 最小值为max_value的20%
        # 难度100: 最小值为max_value的40%
        min_ratio = 0.01 + (self.difficulty / 100) * 0.39  # 0.01 到 0.40
        min_val = max(base_min, int(self.max_value * min_ratio))
        return min_val
    
    def _get_range_for_operation(self, operation_type: str) -> tuple:
        """
        根据运算类型和难度返回合适的数值范围
        :return: (min_val, max_val)
        """
        min_val = self._get_min_value()
        
        if operation_type in ['multiplication', 'division']:
            # 乘除法：表内运算，但避免1×N或N×1
            if self.difficulty < 30:
                return (1, 5)  # 简单：1-5
            elif self.difficulty < 60:
                return (2, 7)  # 中等：2-7，避免1
            else:
                return (3, 9)  # 困难：3-9，避免1和2
        else:
            # 加减法：根据难度调整范围
            if self.difficulty < 30:
                return (min_val, max(5, self.max_value // 2))
            elif self.difficulty < 60:
                return (min_val, max(10, self.max_value * 2 // 3))
            else:
                return (min_val, self.max_value)
    
    def generate_addition(self, fill_type: str = 'result') -> Dict:
        """
        生成加法题目
        :param fill_type: 'result' 填写结果, 'addend' 填写加数
        """
        min_val, max_val = self._get_range_for_operation('addition')
        # 确保a和b都不太小，避免1+2这种简单题目
        a = random.randint(min_val, min(max_val, self.max_value))
        remaining = self.max_value - a
        if remaining < min_val:
            # 如果剩余空间太小，调整a的范围
            a = random.randint(min_val, self.max_value - min_val)
            remaining = self.max_value - a
        b = random.randint(min_val, min(remaining, max_val))
        result = a + b
        
        if fill_type == 'result':
            return {
                'type': 'addition',
                'question': f"{a} + {b} = ___",
                'answer': result,
                'fill_position': 'result'
            }
        else:  # fill_type == 'addend'
            # 随机选择隐藏第一个或第二个加数
            if random.choice([True, False]):
                return {
                    'type': 'addition',
                    'question': f"___ + {b} = {result}",
                    'answer': a,
                    'fill_position': 'addend1'
                }
            else:
                return {
                    'type': 'addition',
                    'question': f"{a} + ___ = {result}",
                    'answer': b,
                    'fill_position': 'addend2'
                }
    
    def generate_subtraction(self, fill_type: str = 'result') -> Dict:
        """
        生成减法题目
        :param fill_type: 'result' 填写结果, 'subtrahend' 填写减数, 'minuend' 填写被减数
        """
        min_val, max_val = self._get_range_for_operation('subtraction')
        # 确保减数和结果都不太小
        result = random.randint(min_val, min(self.max_value - min_val, max_val))
        subtrahend = random.randint(min_val, min(self.max_value - result, max_val))
        minuend = result + subtrahend
        
        if fill_type == 'result':
            return {
                'type': 'subtraction',
                'question': f"{minuend} - {subtrahend} = ___",
                'answer': result,
                'fill_position': 'result'
            }
        elif fill_type == 'subtrahend':
            return {
                'type': 'subtraction',
                'question': f"{minuend} - ___ = {result}",
                'answer': subtrahend,
                'fill_position': 'subtrahend'
            }
        else:  # fill_type == 'minuend'
            return {
                'type': 'subtraction',
                'question': f"___ - {subtrahend} = {result}",
                'answer': minuend,
                'fill_position': 'minuend'
            }
    
    def generate_multiplication(self, fill_type: str = 'result') -> Dict:
        """
        生成乘法题目（表内乘法，1-9）
        :param fill_type: 'result' 填写结果, 'multiplier' 填写乘数
        """
        min_val, max_val = self._get_range_for_operation('multiplication')
        # 避免1×N或N×1这种太简单的题目
        a = random.randint(min_val, max_val)
        b = random.randint(min_val, max_val)
        result = a * b
        
        if fill_type == 'result':
            return {
                'type': 'multiplication',
                'question': f"{a} × {b} = ___",
                'answer': result,
                'fill_position': 'result'
            }
        else:  # fill_type == 'multiplier'
            if random.choice([True, False]):
                return {
                    'type': 'multiplication',
                    'question': f"___ × {b} = {result}",
                    'answer': a,
                    'fill_position': 'multiplier1'
                }
            else:
                return {
                    'type': 'multiplication',
                    'question': f"{a} × ___ = {result}",
                    'answer': b,
                    'fill_position': 'multiplier2'
                }
    
    def generate_division(self, fill_type: str = 'result') -> Dict:
        """
        生成除法题目（表内除法）
        :param fill_type: 'result' 填写结果, 'divisor' 填写除数, 'dividend' 填写被除数
        """
        # 先生成乘法，然后转换为除法
        min_val, max_val = self._get_range_for_operation('division')
        a = random.randint(min_val, max_val)
        b = random.randint(min_val, max_val)
        result = a * b
        
        if fill_type == 'result':
            return {
                'type': 'division',
                'question': f"{result} ÷ {b} = ___",
                'answer': a,
                'fill_position': 'result'
            }
        elif fill_type == 'divisor':
            return {
                'type': 'division',
                'question': f"{result} ÷ ___ = {a}",
                'answer': b,
                'fill_position': 'divisor'
            }
        else:  # fill_type == 'dividend'
            return {
                'type': 'division',
                'question': f"___ ÷ {b} = {a}",
                'answer': result,
                'fill_position': 'dividend'
            }
    
    def generate_addition_multiplication(self, fill_type: str = 'result') -> Dict:
        """
        生成加法+乘法混合运算题目（先乘后加）
        格式：a + b × c = ___
        :param fill_type: 'result' 填写结果, 'operand' 填写操作数
        """
        # 生成乘法部分（表内），根据难度调整
        mult_min, mult_max = self._get_range_for_operation('multiplication')
        mult_a = random.randint(mult_min, mult_max)
        mult_b = random.randint(mult_min, mult_max)
        mult_result = mult_a * mult_b
        
        # 生成加法部分，根据难度调整，确保结果不超过max_value
        add_min, add_max = self._get_range_for_operation('addition')
        max_addend = min(add_max, self.max_value - mult_result)
        if max_addend < add_min:
            max_addend = self.max_value - mult_result
        addend = random.randint(add_min, max(max_addend, add_min))
        final_result = addend + mult_result
        
        if fill_type == 'result':
            return {
                'type': 'addition_multiplication',
                'question': f"{addend} + {mult_a} × {mult_b} = ___",
                'answer': final_result,
                'fill_position': 'result'
            }
        else:  # fill_type == 'operand'
            # 随机选择隐藏加数或乘数
            choice = random.choice(['addend', 'multiplier1', 'multiplier2'])
            if choice == 'addend':
                return {
                    'type': 'addition_multiplication',
                    'question': f"___ + {mult_a} × {mult_b} = {final_result}",
                    'answer': addend,
                    'fill_position': 'addend'
                }
            elif choice == 'multiplier1':
                return {
                    'type': 'addition_multiplication',
                    'question': f"{addend} + ___ × {mult_b} = {final_result}",
                    'answer': mult_a,
                    'fill_position': 'multiplier1'
                }
            else:  # multiplier2
                return {
                    'type': 'addition_multiplication',
                    'question': f"{addend} + {mult_a} × ___ = {final_result}",
                    'answer': mult_b,
                    'fill_position': 'multiplier2'
                }
    
    def generate_addition_division(self, fill_type: str = 'result') -> Dict:
        """
        生成加法+除法混合运算题目（先除后加）
        格式：a + b ÷ c = ___
        :param fill_type: 'result' 填写结果, 'operand' 填写操作数
        """
        # 生成除法部分（表内），根据难度调整
        div_min, div_max = self._get_range_for_operation('division')
        div_a = random.randint(div_min, div_max)
        div_b = random.randint(div_min, div_max)
        div_result = div_a * div_b  # 被除数
        divisor = div_b
        quotient = div_a  # 除法结果
        
        # 生成加法部分，根据难度调整
        add_min, add_max = self._get_range_for_operation('addition')
        max_addend = min(add_max, self.max_value - quotient)
        if max_addend < add_min:
            max_addend = self.max_value - quotient
        addend = random.randint(add_min, max(max_addend, add_min))
        final_result = addend + quotient
        
        if fill_type == 'result':
            return {
                'type': 'addition_division',
                'question': f"{addend} + {div_result} ÷ {divisor} = ___",
                'answer': final_result,
                'fill_position': 'result'
            }
        else:  # fill_type == 'operand'
            choice = random.choice(['addend', 'divisor', 'dividend'])
            if choice == 'addend':
                return {
                    'type': 'addition_division',
                    'question': f"___ + {div_result} ÷ {divisor} = {final_result}",
                    'answer': addend,
                    'fill_position': 'addend'
                }
            elif choice == 'divisor':
                return {
                    'type': 'addition_division',
                    'question': f"{addend} + {div_result} ÷ ___ = {final_result}",
                    'answer': divisor,
                    'fill_position': 'divisor'
                }
            else:  # dividend
                return {
                    'type': 'addition_division',
                    'question': f"{addend} + ___ ÷ {divisor} = {final_result}",
                    'answer': div_result,
                    'fill_position': 'dividend'
                }
    
    def generate_subtraction_multiplication(self, fill_type: str = 'result') -> Dict:
        """
        生成减法+乘法混合运算题目（先乘后减）
        格式：a - b × c = ___
        :param fill_type: 'result' 填写结果, 'operand' 填写操作数
        """
        # 生成乘法部分（表内），根据难度调整
        mult_min, mult_max = self._get_range_for_operation('multiplication')
        mult_a = random.randint(mult_min, mult_max)
        mult_b = random.randint(mult_min, mult_max)
        mult_result = mult_a * mult_b
        
        # 生成减法部分，根据难度调整，确保被减数大于等于乘法结果
        sub_min, sub_max = self._get_range_for_operation('subtraction')
        min_minuend = max(mult_result, sub_min)
        max_minuend = min(self.max_value, mult_result + sub_max)
        minuend = random.randint(min_minuend, max_minuend)
        final_result = minuend - mult_result
        
        if fill_type == 'result':
            return {
                'type': 'subtraction_multiplication',
                'question': f"{minuend} - {mult_a} × {mult_b} = ___",
                'answer': final_result,
                'fill_position': 'result'
            }
        else:  # fill_type == 'operand'
            choice = random.choice(['minuend', 'multiplier1', 'multiplier2'])
            if choice == 'minuend':
                return {
                    'type': 'subtraction_multiplication',
                    'question': f"___ - {mult_a} × {mult_b} = {final_result}",
                    'answer': minuend,
                    'fill_position': 'minuend'
                }
            elif choice == 'multiplier1':
                return {
                    'type': 'subtraction_multiplication',
                    'question': f"{minuend} - ___ × {mult_b} = {final_result}",
                    'answer': mult_a,
                    'fill_position': 'multiplier1'
                }
            else:  # multiplier2
                return {
                    'type': 'subtraction_multiplication',
                    'question': f"{minuend} - {mult_a} × ___ = {final_result}",
                    'answer': mult_b,
                    'fill_position': 'multiplier2'
                }
    
    def generate_subtraction_division(self, fill_type: str = 'result') -> Dict:
        """
        生成减法+除法混合运算题目（先除后减）
        格式：a - b ÷ c = ___
        :param fill_type: 'result' 填写结果, 'operand' 填写操作数
        """
        # 生成除法部分（表内），根据难度调整
        div_min, div_max = self._get_range_for_operation('division')
        div_a = random.randint(div_min, div_max)
        div_b = random.randint(div_min, div_max)
        div_result = div_a * div_b  # 被除数
        divisor = div_b
        quotient = div_a  # 除法结果
        
        # 生成减法部分，根据难度调整，确保被减数大于等于除法结果
        sub_min, sub_max = self._get_range_for_operation('subtraction')
        min_minuend = max(quotient, sub_min)
        max_minuend = min(self.max_value, quotient + sub_max)
        minuend = random.randint(min_minuend, max_minuend)
        final_result = minuend - quotient
        
        if fill_type == 'result':
            return {
                'type': 'subtraction_division',
                'question': f"{minuend} - {div_result} ÷ {divisor} = ___",
                'answer': final_result,
                'fill_position': 'result'
            }
        else:  # fill_type == 'operand'
            choice = random.choice(['minuend', 'divisor', 'dividend'])
            if choice == 'minuend':
                return {
                    'type': 'subtraction_division',
                    'question': f"___ - {div_result} ÷ {divisor} = {final_result}",
                    'answer': minuend,
                    'fill_position': 'minuend'
                }
            elif choice == 'divisor':
                return {
                    'type': 'subtraction_division',
                    'question': f"{minuend} - {div_result} ÷ ___ = {final_result}",
                    'answer': divisor,
                    'fill_position': 'divisor'
                }
            else:  # dividend
                return {
                    'type': 'subtraction_division',
                    'question': f"{minuend} - ___ ÷ {divisor} = {final_result}",
                    'answer': div_result,
                    'fill_position': 'dividend'
                }
    
    def generate_questions(
        self,
        num_pages: int,
        operations: List[str],
        fill_type: str = 'result'
    ) -> List[List[Dict]]:
        """
        生成多页题目
        :param num_pages: 页数（N）
        :param operations: 运算类型列表，支持：
            - 基础运算: 'addition', 'subtraction', 'multiplication', 'division'
            - 混合运算: 'addition_multiplication', 'addition_division', 
                       'subtraction_multiplication', 'subtraction_division'
        :param fill_type: 填写类型 'result' 或 'operand'
        :return: 每页的题目列表
        """
        questions_per_page = 60  # 每页60道题
        all_pages = []
        
        for page in range(num_pages):
            page_questions = []
            for _ in range(questions_per_page):
                op = random.choice(operations)
                
                if op == 'addition':
                    question = self.generate_addition(fill_type if fill_type == 'result' else 'addend')
                elif op == 'subtraction':
                    if fill_type == 'result':
                        question = self.generate_subtraction('result')
                    else:
                        # 随机选择填写减数或被减数
                        question = self.generate_subtraction(random.choice(['subtrahend', 'minuend']))
                elif op == 'multiplication':
                    question = self.generate_multiplication(fill_type if fill_type == 'result' else 'multiplier')
                elif op == 'division':
                    if fill_type == 'result':
                        question = self.generate_division('result')
                    else:
                        # 随机选择填写除数或被除数
                        question = self.generate_division(random.choice(['divisor', 'dividend']))
                elif op == 'addition_multiplication':
                    question = self.generate_addition_multiplication(fill_type)
                elif op == 'addition_division':
                    question = self.generate_addition_division(fill_type)
                elif op == 'subtraction_multiplication':
                    question = self.generate_subtraction_multiplication(fill_type)
                elif op == 'subtraction_division':
                    question = self.generate_subtraction_division(fill_type)
                else:
                    # 默认生成加法
                    question = self.generate_addition(fill_type if fill_type == 'result' else 'addend')
                
                page_questions.append(question)
            
            all_pages.append(page_questions)
        
        return all_pages
