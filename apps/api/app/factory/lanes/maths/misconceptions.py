# ruff: noqa: E501
"""Named wrong procedures (misconceptions) for the Class 10 maths lane. Original wording.

Each id is attached to the wrong options a family builds with that procedure, so a wrong answer
can be explained by what the student likely did, not only marked wrong. Status is draft: nobody
has reviewed these descriptions yet.
"""

from __future__ import annotations

# id -> (title, explanation of the wrong procedure)
TEXT: dict[str, tuple[str, str]] = {
    # ---------------- Quadratic equations
    "MC.QUAD.STD_RHS_IGNORED": (
        "Ignores the right-hand side when collecting",
        "You may have read the left side and ignored the right side.",
    ),
    "MC.QUAD.STD_TERM_ADDED": (
        "Adds the right-hand term instead of removing it",
        "You may have added a term instead of taking it away.",
    ),
    "MC.QUAD.STD_SIGN_NEGATED": (
        "Reverses the sign of the coefficient",
        "You may have collected the terms right but given the opposite sign.",
    ),
    "MC.QUAD.STD_COEFF_POSITION_MIXED": (
        "Reads the wrong coefficient",
        "You may have picked the number next to the one asked for.",
    ),
    "MC.QUAD.CHECK_SIGN_FLIPPED": (
        "Offers the opposite of a root",
        "You may have read the number in the bracket as the answer. Flip its sign.",
    ),
    "MC.QUAD.CHECK_CONSTANT_TERM_USED": (
        "Offers the constant term as a root",
        "You may have thought the plain number is the answer.",
    ),
    "MC.QUAD.CHECK_ONE_OFF": (
        "Offers a value next to a root",
        "You may have been one off and did not test your answer.",
    ),
    "MC.QUAD.CHECK_COEFFICIENT_USED": (
        "Offers a coefficient as a root",
        "You may have used a number from the equation as the answer.",
    ),
    "MC.QUAD.PURE_PLUS_ONLY": (
        "Takes only the positive square root",
        "You may have given only the positive answer. There is a negative one too.",
    ),
    "MC.QUAD.PURE_FORGOT_SQRT": (
        "Forgets to take the square root",
        "You may have stopped at x squared and given it as x.",
    ),
    "MC.QUAD.PURE_MULTIPLIED_NOT_DIVIDED": (
        "Multiplies by the leading coefficient instead of dividing",
        "You may have multiplied to get x squared alone. Divide instead.",
    ),
    "MC.QUAD.PURE_NO_REAL_ROOTS": (
        "Declares no solution by mistake",
        "You may have slipped on a sign and got a negative square.",
    ),
    "MC.QUAD.PURE_SIGN_IGNORED": (
        "Ignores that a square cannot be negative",
        "You may have taken the root of a negative number as positive.",
    ),
    "MC.QUAD.PURE_ONE_NEGATIVE_ROOT": (
        "Gives a single negative root for a negative square",
        "You may have thought the root of a negative number is negative.",
    ),
    "MC.QUAD.PURE_ONE_POSITIVE_ROOT": (
        "Gives a single positive root for a negative square",
        "You may have dropped the minus sign and given only one answer.",
    ),
    "MC.QUAD.PURE_ZERO_ROOT": (
        "Reports zero as the only solution",
        "The student guesses that the only way to satisfy the equation is x = 0.",
    ),
    "MC.QUAD.DIVIDED_BY_X_LOST_ROOT": (
        "Divides by x and loses a root",
        "You may have divided both sides by x. That loses the answer x = 0.",
    ),
    "MC.QUAD.ONE_FACTOR_ONLY": (
        "Solves from one factor only",
        "You may have set only the x part to zero.",
    ),
    "MC.QUAD.FACTOR_SIGN_SLIP": (
        "Wrong sign on the second root",
        "You may have written one answer with the wrong sign.",
    ),
    "MC.QUAD.SECOND_ROOT_SIGN_ONLY": (
        "Reports only the second root with its sign changed",
        "The student loses the zero root and flips the sign of the other.",
    ),
    "MC.QUAD.FACTOR_SIGN_READ": (
        "Reads roots straight from the brackets",
        "You may have read each bracket number as the answer. Flip its sign.",
    ),
    "MC.QUAD.FACTOR_ONE_SIGN": (
        "Changes the sign of only one root",
        "You may have fixed one bracket's sign but not the other.",
    ),
    "MC.QUAD.FACTOR_ONE_ROOT_ONLY": (
        "Stops after one root",
        "You may have solved one bracket and forgotten the other.",
    ),
    "MC.QUAD.FACTOR_SUM_PRODUCT_CONFUSED": (
        "Reports the sum and product as the roots",
        "The student mixes up what the sum and product of two numbers are used for.",
    ),
    "MC.QUAD.BRACKET_COEFF_IGNORED": (
        "Ignores the coefficient of x inside a bracket",
        "You may have never divided by the number in front of x.",
    ),
    "MC.QUAD.BRACKET_COEFF_INVERTED": (
        "Divides the wrong way round",
        "You may have turned the fraction upside down when undoing the bracket.",
    ),
    "MC.QUAD.FORMULA_B_SIGN": (
        "Uses b instead of minus b",
        "You may have forgotten the minus sign in front of b.",
    ),
    "MC.QUAD.FORMULA_FORGOT_2A": (
        "Divides by a instead of twice a",
        "You may have divided by a only. The bottom of the formula is 2a.",
    ),
    "MC.QUAD.FORMULA_DIVIDE_ONE_TERM": (
        "Divides only the square-root part",
        "You may have divided only one part by 2a, not both.",
    ),
    "MC.QUAD.FORMULA_FORGOT_A": (
        "Divides by 2 and ignores the leading coefficient",
        "You may have divided by 2 and forgotten the a.",
    ),
    "MC.QUAD.FORMULA_DISC_SIGN": (
        "Adds instead of subtracting in the discriminant",
        "You may have added 4ac under the root. Take it away.",
    ),
    "MC.QUAD.DISC_SIGN_OF_4AC": (
        "Adds 4ac in the discriminant",
        "You may have added 4ac where you should take it away.",
    ),
    "MC.QUAD.DISC_FORGOT_FOUR": (
        "Forgets the factor 4",
        "You may have used ac where 4ac belongs.",
    ),
    "MC.QUAD.DISC_DOUBLED_B": (
        "Doubles b instead of squaring it",
        "You may have written 2b where b squared belongs.",
    ),
    "MC.QUAD.DISC_NEGATIVE_B_SQUARED": (
        "Carries the minus into the square",
        "You may have got a negative when squaring a negative b. A square is never negative.",
    ),
    "MC.QUAD.NATURE_DISC_SIGN_REVERSED": (
        "Reads the sign of the discriminant backwards",
        "You may have mixed up what plus and minus values tell you.",
    ),
    "MC.QUAD.NATURE_ZERO_ONLY_TESTED": (
        "Only tests whether the discriminant is zero",
        "You may have treated every value except zero as the same case.",
    ),
    "MC.QUAD.NATURE_EQUAL_ROOTS_MISSED": (
        "Misses the equal-roots case",
        "You may have thought zero still gives two different answers.",
    ),
    "MC.QUAD.NATURE_ZERO_DISC_NO_ROOTS": (
        "Thinks zero discriminant means no roots",
        "You may have read zero as nothing and said no answers.",
    ),
    "MC.QUAD.NATURE_ONE_REAL_ONE_NOT": (
        "Mixed real and non-real roots",
        "You may have thought one answer can be real and one not.",
    ),
    "MC.QUAD.K_POSITIVE_ONLY": (
        "Gives only the positive value of the parameter",
        "You may have forgotten the negative answer after taking the square root.",
    ),
    "MC.QUAD.K_FORGOT_SQRT": (
        "Forgets the square root on the parameter",
        "You may have stopped at k squared. Take the square root.",
    ),
    "MC.QUAD.K_FORGOT_FACTOR_FOUR": (
        "Forgets the 4 in the discriminant condition",
        "You may have set b squared equal to ac. It should be 4ac.",
    ),
    "MC.QUAD.K_ONE_SIGN_PAIR": (
        "Mismatched pair for the parameter",
        "The student combines a correct negative value with an unrelated positive one.",
    ),
    "MC.QUAD.K_SIGN": (
        "Reverses the sign of the parameter",
        "You may have the right size for k but the wrong sign.",
    ),
    "MC.QUAD.K_HALF_FACTOR": (
        "Uses 2 where 4 is needed",
        "You may have written 2kc where 4kc belongs.",
    ),
    "MC.QUAD.K_INVERTED": (
        "Inverts the parameter",
        "The student rearranges the condition upside down.",
    ),
    "MC.QUAD.FORM_SUM_SIGN": (
        "Wrong sign on the middle term",
        "You may have written the sum of the answers with a plus. It needs a minus.",
    ),
    "MC.QUAD.FORM_PRODUCT_SIGN": (
        "Wrong sign on the constant",
        "You may have flipped the sign of the last two numbers.",
    ),
    "MC.QUAD.SUM_PRODUCT_CONFUSED": (
        "Swaps sum and product",
        "You may have swapped the number with x and the plain number.",
    ),
    "MC.QUAD.FORM_BOTH_SIGNS_FLIPPED": (
        "Both coefficients take the wrong sign",
        "The student reverses the signs of the constant and the x coefficient.",
    ),
    "MC.QUAD.CS_SIGN_OF_HALF": (
        "Wrong sign inside the bracket",
        "You may have halved the number but used the wrong sign.",
    ),
    "MC.QUAD.CS_NOT_HALVED": (
        "Does not halve the coefficient",
        "You may have used the whole number in front of x.",
    ),
    "MC.QUAD.CS_SQUARED_INSTEAD": (
        "Squares instead of halving",
        "You may have squared the number instead of halving it.",
    ),
    "MC.QUAD.CS_ADDED_NOT_SUBTRACTED": (
        "Adds the constant instead of moving it",
        "You may have added the plain number instead of taking it away.",
    ),
    "MC.QUAD.CS_NOT_SQUARED": (
        "Forgets to square the half",
        "You may have added half the number and forgotten to square it.",
    ),
    "MC.QUAD.CS_SIGN_SWAPPED": (
        "Subtracts in the wrong order",
        "You may have found the right parts but took them away backwards.",
    ),
    "MC.QUAD.WORD_LARGER_REPORTED": (
        "Reports the larger number",
        "You may have solved it right but given the other number.",
    ),
    "MC.QUAD.WORD_NEGATIVE_ROOT_KEPT": (
        "Keeps the root that does not fit",
        "You may have kept a negative answer. This quantity cannot be negative.",
    ),
    "MC.QUAD.WORD_SETUP_WRONG_DIFFERENCE": (
        "Sets the numbers up with the wrong gap",
        "You may have taken the difference away where it should be added.",
    ),
    "MC.QUAD.WORD_SUM_USED_FOR_PRODUCT": (
        "Adds where the story multiplies",
        "The student writes a sum of the two numbers in place of their product.",
    ),
    "MC.QUAD.WORD_LENGTH_REPORTED": (
        "Reports the length instead of the breadth",
        "You may have given the other side.",
    ),
    "MC.QUAD.WORD_SEMIPERIMETER_FOR_SIDE": (
        "Reports the semi-perimeter",
        "You may have added two sides and given that as one side.",
    ),
    "MC.QUAD.WORD_BREADTH_REPORTED": (
        "Reports the breadth instead of the length",
        "You may have given the number you named, not the asked one.",
    ),
    "MC.QUAD.WORD_DIFFERENCE_ADDED_TWICE": (
        "Adds the difference twice",
        "You may have added the given difference two times.",
    ),
    "MC.QUAD.WORD_HALF_PERIMETER": (
        "Uses half the perimeter",
        "You may have added length and breadth once and forgotten to double.",
    ),
    "MC.QUAD.WORD_AREA_NOT_PERIMETER": (
        "Uses the area where the perimeter is needed",
        "You may have used the area where the distance round belongs.",
    ),
    "MC.QUAD.WORD_LENGTH_AS_BREADTH": (
        "Swaps the length and the breadth",
        "You may have swapped the two sides before finding the distance round.",
    ),
    "MC.QUAD.WORD_FORGOT_FINAL_STEP": (
        "Stops before the final step",
        "You may have found the distance round but not the cost.",
    ),
    "MC.QUAD.WORD_OTHER_SIDE_REPORTED": (
        "Reports the other side",
        "You may have given the side that was not asked about.",
    ),
    "MC.QUAD.WORD_HYPOTENUSE_MINUS_DIFFERENCE": (
        "Subtracts the difference from the longest side",
        "You may have guessed a side from the longest side.",
    ),
    "MC.QUAD.WORD_SIDES_SUMMED": (
        "Mixes the longest side and a leg",
        "You may have taken a short side from the longest one.",
    ),
    "MC.QUAD.WORD_OTHER_SPEED_REPORTED": (
        "Reports the other speed",
        "You may have given the speed that was not asked about.",
    ),
    "MC.QUAD.WORD_INCREASE_SUBTRACTED": (
        "Subtracts the speed increase",
        "You may have taken the increase away from the usual speed.",
    ),
    "MC.QUAD.WORD_INCREASE_ONLY": (
        "Reports the speed increase itself",
        "The student answers with the given change in speed.",
    ),
    # ---------------- Arithmetic progressions
    "MC.AP.DIFF_SIGN_REVERSED": (
        "Wrong order when subtracting",
        "You may have taken the later number away from the earlier one. Try the other way round.",
    ),
    "MC.AP.DIFF_AS_RATIO": (
        "Divides instead of subtracting",
        "You may have divided the two numbers instead of taking one away.",
    ),
    "MC.AP.DIFF_FIRST_TERM_GIVEN": (
        "Reports the first term",
        "You may have given the first number, not the step.",
    ),
    "MC.AP.DIFF_SKIPPED_TERM": (
        "Subtracts terms that are not neighbours",
        "You may have compared two numbers that are not side by side.",
    ),
    "MC.AP.DIFF_LAST_TERM_GIVEN": (
        "Reports the last listed term",
        "You may have given the last number, not the step.",
    ),
    "MC.AP.RATIO_FOR_DIFFERENCE": (
        "Mistakes a constant ratio for a constant difference",
        "You may have accepted a list that multiplies each time. It must add.",
    ),
    "MC.AP.CHECKED_TWO_TERMS_ONLY": (
        "Checks only the first gap",
        "You may have checked only the first two numbers, not the rest.",
    ),
    "MC.AP.DIFFERENCES_INCREASING_ACCEPTED": (
        "Accepts steadily growing steps",
        "You may have accepted a list whose steps keep growing. The step must stay the same.",
    ),
    "MC.AP.NTH_N_FOR_N_MINUS_1": (
        "Uses n instead of n minus 1",
        "You may have used the place number. You need one step fewer than that.",
    ),
    "MC.AP.NTH_D_ADDED_NOT_MULTIPLIED": (
        "Adds the difference instead of multiplying",
        "You may have added the step once. You must add it again and again.",
    ),
    "MC.AP.NTH_SIGN_OF_D_FLIPPED": (
        "Subtracts the difference",
        "You may have gone the wrong way. Add the step when the list goes up.",
    ),
    "MC.AP.NTH_FIRST_TERM_DROPPED": (
        "Forgets the first term",
        "The student reports only the total of the steps.",
    ),
    "MC.AP.NTH_OFF_BY_ONE_LOW": (
        "Counts two fewer steps than needed",
        "You may have taken two steps fewer than the place number.",
    ),
    "MC.AP.FIND_N_FORGOT_PLUS_ONE": (
        "Forgets to add 1 to the step count",
        "You may have counted the steps and given that as the place. Add 1 more.",
    ),
    "MC.AP.FIND_N_OVERCOUNT": (
        "Counts one position too many",
        "You may have added 1 two times when finding the place.",
    ),
    "MC.AP.FIND_N_DIFFERENCE_NOT_DIVIDED": (
        "Stops before dividing by the difference",
        "You may have stopped after taking away the first number. Now count the steps.",
    ),
    "MC.AP.FIND_N_VALUE_OVER_DIFFERENCE": (
        "Divides the target by the difference",
        "The student ignores the first term and divides the target value directly.",
    ),
    "MC.AP.TWO_TERMS_DIFF_NOT_DIVIDED": (
        "Does not share the change over the steps",
        "You may have used the gap between two numbers several steps apart.",
    ),
    "MC.AP.TWO_TERMS_STARTED_FROM_GIVEN_TERM": (
        "Starts counting from a given term as if it were the first",
        "You may have used the first number given as the start.",
    ),
    "MC.AP.SUM_FORGOT_HALF": (
        "Forgets to halve",
        "You may have multiplied by n and forgotten to divide by 2.",
    ),
    "MC.AP.SUM_N_FOR_N_MINUS_1": (
        "Uses n instead of n minus 1 in the sum",
        "You may have used a count that is one too big.",
    ),
    "MC.AP.SUM_NO_DOUBLE_A": (
        "Forgets to double the first term",
        "You may have used a where 2a belongs.",
    ),
    "MC.AP.SUM_AS_NTH_TERM": (
        "Gives the last term instead of the sum",
        "You may have given one number from the list, not the total.",
    ),
    "MC.AP.SUM_COUNT_FORGOT_PLUS_ONE": (
        "Counts the terms one short",
        "You may have counted the gaps between numbers instead of the numbers.",
    ),
    "MC.AP.SUM_LAST_TERM_AS_COUNT": (
        "Uses the last term as the number of terms",
        "You may have put the last number where the count belongs.",
    ),
    "MC.AP.SUM_FORGOT_COUNT_AND_HALF": (
        "Adds only the first and last terms",
        "You may have only added the first and last numbers.",
    ),
    "MC.AP.SUMN_OTHER_ROOT_KEPT": (
        "Keeps the root that is not a count",
        "You may have kept an answer that is negative or a fraction. A count cannot be that.",
    ),
    "MC.AP.SUMN_OFF_BY_ONE": (
        "Off by one in the number of terms",
        "You may have solved it right and then added or taken away 1.",
    ),
    "MC.AP.SUMN_DIVIDED_BY_FIRST_TERM": (
        "Divides the sum by the first term",
        "You may have used the count times the first number.",
    ),
    "MC.AP.TERM_IS_SUM": (
        "Reports the sum instead of the term",
        "You may have given the total so far, not the single number.",
    ),
    "MC.AP.TERM_FROM_SUM_AVERAGE": (
        "Divides the sum by n",
        "You may have found the average and called it the answer.",
    ),
    "MC.AP.TERM_FROM_SUM_WRONG_INDEX": (
        "Subtracts the wrong earlier sum",
        "You may have gone back two totals instead of one.",
    ),
    "MC.AP.TERM_FROM_SUM_NEXT_SUM": (
        "Takes the sums either side",
        "You may have taken one total from the next. That gives two numbers.",
    ),
    "MC.AP.D_FROM_SUM_COEFF_NOT_DOUBLED": (
        "Forgets to double the coefficient",
        "You may have used the number in front of n squared. Double it.",
    ),
    "MC.AP.D_FROM_SUM_FIRST_TERM": (
        "Reports the first term",
        "You may have given the first number, not the step.",
    ),
    "MC.AP.D_FROM_SUM_SECOND_TERM": (
        "Reports the second term",
        "You may have given the second number, not the step.",
    ),
    "MC.AP.D_FROM_SUM_LINEAR_COEFF": (
        "Reads the difference from the linear term",
        "You may have used the n number as the step.",
    ),
    "MC.AP.WORD_TOTAL_REPORTED": (
        "Reports the total for a single term",
        "The student answers with the sum of all rows.",
    ),
    "MC.AP.WORD_LAST_REPORTED": (
        "Reports the last value for the total",
        "You may have given the last number instead of the total.",
    ),
    "MC.AP.COUNT_FORGOT_PLUS_ONE": (
        "Counts the multiples one short",
        "You may have taken one position from another and forgotten to add 1.",
    ),
    "MC.AP.ENDPOINTS_USED_NOT_MULTIPLES": (
        "Uses the range ends instead of the multiples",
        "You may have used the range ends, which are not multiples.",
    ),
    "MC.AP.MULTIPLES_STARTED_FROM_FIRST": (
        "Starts adding multiples from the very first",
        "You may have counted multiples that sit below the range.",
    ),
    # ---------------- Trigonometry
    "MC.TRIG.SIN_COS_MIXED": (
        "Mixes up sine and cosine",
        "You may have used the near side where the far side belongs.",
    ),
    "MC.TRIG.RATIO_INVERTED": (
        "Writes the ratio upside down",
        "You may have turned the fraction upside down.",
    ),
    "MC.TRIG.SIN_AS_OPP_OVER_ADJ": (
        "Takes sine as opposite over adjacent",
        "You may have put the near side where the longest side belongs.",
    ),
    "MC.TRIG.SIN_AS_ADJ_OVER_OPP": (
        "Takes sine as adjacent over opposite",
        "Both the numerator and the denominator are chosen wrongly.",
    ),
    "MC.TRIG.COS_AS_ADJ_OVER_OPP": (
        "Takes cosine as adjacent over opposite",
        "You may have put the opposite side where the longest side belongs.",
    ),
    "MC.TRIG.COS_AS_OPP_OVER_ADJ": (
        "Takes cosine as opposite over adjacent",
        "Both sides of the ratio are chosen wrongly.",
    ),
    "MC.TRIG.TAN_AS_OPP_OVER_HYP": (
        "Takes tangent as opposite over hypotenuse",
        "You may have put the longest side at the bottom.",
    ),
    "MC.TRIG.TAN_AS_ADJ_OVER_HYP": (
        "Takes tangent as adjacent over hypotenuse",
        "You may have used the sides that belong to cosine.",
    ),
    "MC.TRIG.HYP_AS_SUM_OF_LEGS": (
        "Takes the hypotenuse as the sum of the legs",
        "The student adds the two legs instead of using the right-triangle relation.",
    ),
    "MC.TRIG.SWAPPED_SIN_COS_VALUES": (
        "Swaps the sine and cosine table values",
        "You may have mixed up the values of sine and cosine.",
    ),
    "MC.TRIG.SQUARE_DROPPED": (
        "Forgets to square the ratio",
        "You may have found each ratio and forgotten to square it.",
    ),
    "MC.TRIG.ANGLES_ADDED_INSIDE": (
        "Adds the angles inside one ratio",
        "You may have split sin (A + B) into two sines.",
    ),
    "MC.TRIG.TAN_VALUE_AS_SIN_VALUE": (
        "Uses the sine value for the tangent",
        "You may have used the sine values for tangent.",
    ),
    "MC.TRIG.OPERATION_MIXED_UP": (
        "Uses the wrong operation between terms",
        "You may have got both values right but added instead of multiplied.",
    ),
    "MC.TRIG.COMPLEMENT_GAVE_ZERO": (
        "Concludes that complementary terms cancel to zero",
        "You may have seen matching parts and thought they cancel.",
    ),
    "MC.TRIG.COMPLEMENT_GAVE_ONE": (
        "Concludes the expression equals one",
        "You may have used a rule that does not fit this question.",
    ),
    "MC.TRIG.COMPLEMENT_GAVE_TWO": (
        "Adds two equal values",
        "You may have seen two parts equal to one and added them.",
    ),
    "MC.TRIG.COMPLEMENT_GAVE_MINUS_ONE": (
        "Gets a stray minus sign",
        "You may have carried a minus sign into the answer by mistake.",
    ),
    "MC.TRIG.PYTHAG_NOT_SQUARED": (
        "Forgets the squares in the identity",
        "You may have written cos A as 1 minus sin A. Both need squares.",
    ),
    "MC.TRIG.SQUARE_NOT_ROOTED": (
        "Stops at the square of the ratio",
        "You may have squared the ratio and forgotten the square root.",
    ),
    "MC.TRIG.GIVEN_REPEATED": (
        "Repeats the given ratio",
        "You may have given back the value you were told.",
    ),
    "MC.TRIG.WRONG_RATIO_REPORTED": (
        "Reports the third ratio",
        "The student finds a different ratio from the one asked.",
    ),
    "MC.TRIG.HD_TAN_INVERTED": (
        "Divides by the tangent instead of multiplying",
        "You may have turned the ratio upside down.",
    ),
    "MC.TRIG.HD_SIN_FOR_TAN": (
        "Uses sine instead of tangent",
        "You may have used the sloping side, which is not known.",
    ),
    "MC.TRIG.HD_COS_FOR_TAN": (
        "Uses cosine instead of tangent",
        "You may have picked the near side over the longest side.",
    ),
    "MC.TRIG.HD_SLANT_REPORTED": (
        "Reports the sloping distance",
        "You may have found the sloping side, not the height or distance.",
    ),
    "MC.TRIG.HD_MULTIPLIED_NOT_DIVIDED": (
        "Multiplies where division is needed",
        "You may have multiplied when the unknown sits under the ratio. Divide instead.",
    ),
    "MC.TRIG.HD_SIN_COS_SWAPPED": (
        "Swaps sine and cosine in the figure",
        "You may have matched the ratio to the wrong side.",
    ),
    "MC.TRIG.HD_TAN_FOR_SIN_COS": (
        "Uses tangent where sine or cosine is needed",
        "You may have picked a ratio that leaves out the ladder.",
    ),
    "MC.TRIG.HD_DIVIDED_NOT_MULTIPLIED": (
        "Divides where multiplication is needed",
        "You may have divided the ladder length by the ratio. Multiply instead.",
    ),
    "MC.TRIG.HD_HALF_LENGTH_ONLY": (
        "Halves the length without a ratio",
        "The student assumes the side is half the ladder.",
    ),
    "MC.TRIG.HD_SIDE_REPORTED": (
        "Reports the given side as the ladder",
        "The student answers with the number from the question.",
    ),
    "MC.TRIG.HD_DEPRESSION_FROM_VERTICAL": (
        "Measures the angle of depression from the vertical",
        "You may have measured the angle from the wall. It is measured from the level line.",
    ),
    "MC.TRIG.HD_SEPARATION_AS_HEIGHT": (
        "Reports the distance walked as the height",
        "You may have used the gap between places as the height.",
    ),
    "MC.TRIG.HD_FIRST_ANGLE_ONLY": (
        "Uses only the first angle",
        "You may have used the distance walked as the whole ground distance.",
    ),
    "MC.TRIG.HD_SECOND_ANGLE_ONLY": (
        "Uses only the second angle",
        "You may have used the distance walked as the last ground distance.",
    ),
    "MC.TRIG.HD_DISTANCES_ADDED": (
        "Adds the two ground distances",
        "You may have added two distances that you should take away.",
    ),
}
