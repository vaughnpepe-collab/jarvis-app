"use client";

import React, { createContext, useContext, useState, useCallback } from "react";

export interface CartItem {
  id:       string;
  slug:     string;
  name:     string;
  price:    number;
  size:     string;
  color:    string;
  image:    string;
  quantity: number;
}

interface CartContextValue {
  items:        CartItem[];
  isOpen:       boolean;
  itemCount:    number;
  subtotal:     number;
  addItem:      (item: Omit<CartItem, "quantity">) => void;
  removeItem:   (id: string, size: string) => void;
  updateQty:    (id: string, size: string, qty: number) => void;
  openCart:     () => void;
  closeCart:    () => void;
  clearCart:    () => void;
}

const CartContext = createContext<CartContextValue | null>(null);

export function CartProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = useState<CartItem[]>([]);
  const [isOpen, setIsOpen] = useState(false);

  const addItem = useCallback((incoming: Omit<CartItem, "quantity">) => {
    setItems((prev) => {
      const existing = prev.find(
        (i) => i.id === incoming.id && i.size === incoming.size
      );
      if (existing) {
        return prev.map((i) =>
          i.id === incoming.id && i.size === incoming.size
            ? { ...i, quantity: i.quantity + 1 }
            : i
        );
      }
      return [...prev, { ...incoming, quantity: 1 }];
    });
    setIsOpen(true);
  }, []);

  const removeItem = useCallback((id: string, size: string) => {
    setItems((prev) => prev.filter((i) => !(i.id === id && i.size === size)));
  }, []);

  const updateQty = useCallback((id: string, size: string, qty: number) => {
    if (qty < 1) return;
    setItems((prev) =>
      prev.map((i) =>
        i.id === id && i.size === size ? { ...i, quantity: qty } : i
      )
    );
  }, []);

  const clearCart  = useCallback(() => setItems([]), []);
  const openCart   = useCallback(() => setIsOpen(true), []);
  const closeCart  = useCallback(() => setIsOpen(false), []);

  const itemCount = items.reduce((s, i) => s + i.quantity, 0);
  const subtotal  = items.reduce((s, i) => s + i.price * i.quantity, 0);

  return (
    <CartContext.Provider
      value={{ items, isOpen, itemCount, subtotal, addItem, removeItem, updateQty, openCart, closeCart, clearCart }}
    >
      {children}
    </CartContext.Provider>
  );
}

export function useCart(): CartContextValue {
  const ctx = useContext(CartContext);
  if (!ctx) throw new Error("useCart must be used within CartProvider");
  return ctx;
}
