.. README file for module discount_purchase
This module for incremental discount system in purchase order for decrease unit price in every purchase order line
New Model : discount.purchase
list field
- order_line_id (many2one to purchase.order.line)
- type (selection percentage and fixed amount
- amount (float amount)
- disc_value (discount value)
- subtotal (price after using this discount)

New Field in purchase.order.line
- purch_discount_ids (one2many to discount.purchase)
- discount (value of discount in this line)
- net_price (unit price after disocunt, not show)

Flow :
- After create purchase order then save
- will be show pencil button after discount, if click will show wizard view list discount
- Adding discount 
  Type Percentage formula is amount discount * net price (unit price after discount)
  Type Fixed Amount formula is net price - amount discount
- Have 3 button in wizard
  *Confirm button for change discount value on this line based on list discount adding (just 1 line)
  *Apply All button for apply list discount adding to all order line of that purchase order
  *Discard for cancel
- Then can confirm Purchase Order and cannot edit discount again after state is not RFQ, but can show list of discount per line
- When create vendor bill discount in purchase line will be added to vendor bill line


