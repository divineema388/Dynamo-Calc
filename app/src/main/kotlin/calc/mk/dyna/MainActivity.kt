package calc.mk.dyna

import android.animation.AnimatorInflater
import android.animation.AnimatorSet
import android.os.Bundle
import android.view.View
import android.view.animation.AnimationUtils
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import calc.mk.dyna.databinding.ActivityMainBinding
import java.math.BigDecimal
import java.text.DecimalFormat

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding

    private var currentInput: String = "0"
    private var lastOperation: String? = null
    private var firstOperand: BigDecimal? = null
    private var isNewInput: Boolean = true // To check if the current input is a new number or continuation
    private var isDecimalAdded: Boolean = false
    private var historyText: String = ""

    private val decimalFormat = DecimalFormat("#,##0.########").apply {
        isGroupingUsed = true
        maximumFractionDigits = 8
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        // Initialize UI
        updateDisplay()
        updateHistoryDisplay()

        // Set up button click listeners
        setClickListeners()
    }

    private fun setClickListeners() {
        // Digit buttons
        val digitButtons = listOf(
            binding.button0, binding.button1, binding.button2, binding.button3,
            binding.button4, binding.button5, binding.button6, binding.button7,
            binding.button8, binding.button9
        )
        digitButtons.forEach { button ->
            button.setOnClickListener { onDigitClick(it) }
        }

        // Operator buttons
        val operatorButtons = listOf(
            binding.buttonAdd, binding.buttonSubtract, binding.buttonMultiply,
            binding.buttonDivide
        )
        operatorButtons.forEach { button ->
            button.setOnClickListener { onOperatorClick(it) }
        }

        // Other functional buttons
        binding.buttonClear.setOnClickListener { onClearClick(it) }
        binding.buttonPlusMinus.setOnClickListener { onPlusMinusClick(it) }
        binding.buttonPercentage.setOnClickListener { onPercentageClick(it) }
        binding.buttonDecimalPoint.setOnClickListener { onDecimalClick(it) }
        binding.buttonEquals.setOnClickListener { onEqualsClick(it) }
    }

    private fun onDigitClick(view: View) {
        animateButtonPress(view)
        val button = view as Button
        val digit = button.text.toString()

        if (isNewInput) {
            currentInput = digit
            isNewInput = false
            isDecimalAdded = false // Reset decimal flag for new input
        } else {
            if (currentInput == "0" && digit != ".") {
                currentInput = digit
            } else {
                currentInput += digit
            }
        }
        updateDisplay()
    }

    private fun onOperatorClick(view: View) {
        animateButtonPress(view)
        val button = view as Button
        val operator = button.text.toString()

        if (firstOperand == null || !isNewInput) {
            calculateResult(true) // Calculate if there's a pending operation and new input
            firstOperand = currentInput.toBigDecimalOrNull() ?: BigDecimal.ZERO
        }
        lastOperation = operator
        historyText = "${formatNumber(firstOperand!!)} $operator "
        isNewInput = true // Next digit input will start a new number
        isDecimalAdded = false // Reset decimal for next number
        updateHistoryDisplay()
        updateDisplay() // Update display to show current input as the first operand
    }

    private fun onEqualsClick(view: View) {
        animateButtonPress(view)
        if (firstOperand != null && lastOperation != null && !isNewInput) {
            calculateResult(false)
            lastOperation = null
            isNewInput = true
            isDecimalAdded = currentInput.contains(".") // Keep decimal flag if result has one
            historyText = "" // Clear history after equals
            updateHistoryDisplay()
        } else if (firstOperand != null && lastOperation == null) {
            // If equals is pressed after a result without a new operation
            // Do nothing or repeat last operation (for advanced calc)
            // For basic, just ensure the current number is the result
            historyText = ""
            updateHistoryDisplay()
        }
    }

    private fun onClearClick(view: View) {
        animateButtonPress(view)
        currentInput = "0"
        lastOperation = null
        firstOperand = null
        isNewInput = true
        isDecimalAdded = false
        historyText = ""
        updateDisplay()
        updateHistoryDisplay()
    }

    private fun onPlusMinusClick(view: View) {
        animateButtonPress(view)
        val number = currentInput.toBigDecimalOrNull()
        if (number != null && number != BigDecimal.ZERO) {
            currentInput = (number.negate()).stripTrailingZeros().toPlainString()
            // Ensure no scientific notation for very small or large numbers after negation if possible
            if (currentInput.contains("E")) {
                currentInput = decimalFormat.format(BigDecimal(currentInput))
            }
        }
        updateDisplay()
    }

    private fun onPercentageClick(view: View) {
        animateButtonPress(view)
        val number = currentInput.toBigDecimalOrNull()
        if (number != null) {
            currentInput = (number.divide(BigDecimal(100))).stripTrailingZeros().toPlainString()
            // Ensure no scientific notation
            if (currentInput.contains("E")) {
                currentInput = decimalFormat.format(BigDecimal(currentInput))
            }
            isDecimalAdded = currentInput.contains(".")
        }
        updateDisplay()
    }

    private fun onDecimalClick(view: View) {
        animateButtonPress(view)
        if (!isDecimalAdded) {
            if (isNewInput) {
                currentInput = "0."
                isNewInput = false
            } else {
                currentInput += "."
            }
            isDecimalAdded = true
        }
        updateDisplay()
    }

    private fun calculateResult(isIntermediate: Boolean) {
        if (firstOperand == null || lastOperation == null) return

        val secondOperand = currentInput.toBigDecimalOrNull() ?: BigDecimal.ZERO
        var result: BigDecimal? = null

        try {
            when (lastOperation) {
                "+" -> result = firstOperand!!.add(secondOperand)
                "−" -> result = firstOperand!!.subtract(secondOperand)
                "×" -> result = firstOperand!!.multiply(secondOperand)
                "÷" -> {
                    if (secondOperand == BigDecimal.ZERO) {
                        currentInput = "Error"
                        firstOperand = null
                        lastOperation = null
                        historyText = ""
                        updateDisplay()
                        updateHistoryDisplay()
                        return
                    }
                    // Use MathContext for division to handle precision
                    result = firstOperand!!.divide(secondOperand, 8, BigDecimal.ROUND_HALF_UP)
                }
            }
        } catch (e: Exception) {
            currentInput = "Error"
            firstOperand = null
            lastOperation = null
            historyText = ""
            updateDisplay()
            updateHistoryDisplay()
            return
        }

        result?.let {
            currentInput = formatNumber(it)
            firstOperand = it // Store result as first operand for chained operations
            if (!isIntermediate) {
                // Animate result display only when equals is pressed
                animateResultDisplay(binding.tvDisplayResult)
            }
        }
    }

    private fun updateDisplay() {
        binding.tvDisplayResult.text = currentInput
    }

    private fun updateHistoryDisplay() {
        binding.tvDisplayHistory.text = historyText
        // Animate history display if it changes significantly
        if (historyText.isNotEmpty() && binding.tvDisplayHistory.visibility == View.GONE) {
            binding.tvDisplayHistory.visibility = View.VISIBLE
            binding.tvDisplayHistory.startAnimation(AnimationUtils.loadAnimation(this, R.anim.fade_in))
        } else if (historyText.isEmpty() && binding.tvDisplayHistory.visibility == View.VISIBLE) {
            binding.tvDisplayHistory.startAnimation(AnimationUtils.loadAnimation(this, R.anim.fade_out))
            binding.tvDisplayHistory.visibility = View.GONE
        }
    }

    private fun formatNumber(number: BigDecimal): String {
        return try {
            number.stripTrailingZeros().toPlainString() // Remove trailing zeros without scientific notation
        } catch (e: Exception) {
            number.toPlainString() // Fallback
        }
    }

    private fun animateButtonPress(view: View) {
        val animator = AnimatorInflater.loadAnimator(this, R.anim.button_press_anim) as AnimatorSet
        animator.setTarget(view)
        animator.start()
    }

    private fun animateResultDisplay(view: TextView) {
        val animation = AnimationUtils.loadAnimation(this, R.anim.result_fade_in)
        view.startAnimation(animation)
    }
}