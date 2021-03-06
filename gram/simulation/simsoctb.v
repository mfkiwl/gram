// This file is Copyright (c) 2020 LambdaConcept <contact@lambdaconcept.com>

`timescale 1 ns / 1 ns

module simsoctb;
  // GSR & PUR init requires for Lattice models
  GSR GSR_INST (
    .GSR(1'b1)
  );
  PUR PUR_INST (
    .PUR (1'b1)
  );

  reg clkin;
  wire sync;
  wire sync2x;
  wire dramsync;
  wire init;

  // Generate 100 Mhz clock
  always 
    begin
      clkin = 1;
      #5;
      clkin = 0;
      #5;
    end

  // DDR3 init
  wire dram_ck;
  wire dram_cke;
  wire dram_we_n;
  wire dram_ras_n;
  wire dram_cas_n;
  wire [15:0] dram_dq;
  inout wire [1:0] dram_dqs;
  inout wire [1:0] dram_dqs_n;
  wire [13:0] dram_a;
  wire [2:0] dram_ba;
  wire [1:0] dram_dm;
  wire dram_odt;
  wire [1:0] dram_tdqs_n;
  reg dram_rst = 0;

  ddr3 #(
    .check_strict_timing(0)
  ) ram_chip (
    .rst_n(~dram_rst),
    .ck(dram_ck),
    .ck_n(~dram_ck),
    .cke(dram_cke),
    .cs_n(1'b0),
    .ras_n(dram_ras_n),
    .cas_n(dram_cas_n),
    .we_n(dram_we_n),
    .dm_tdqs(dram_dm),
    .ba(dram_ba),
    .addr(dram_a),
    .dq(dram_dq),
    .dqs(dram_dqs),
    .dqs_n(dram_dqs_n),
    .tdqs_n(dram_tdqs_n),
    .odt(dram_odt)
  );

  assign dram_dqs_n = (dram_dqs != 2'hz) ? ~dram_dqs : 2'hz;

  // Wishbone
  reg [31:0] wishbone_adr = 0;
  reg [31:0] wishbone_dat_w = 0;
  wire [31:0] wishbone_dat_r;
  reg [3:0] wishbone_sel = 0;
  reg wishbone_cyc = 0;
  reg wishbone_stb = 0;
  reg wishbone_we = 0;
  wire wishbone_ack;

  //defparam ram_chip.
  
  top simsoctop (
    .ddr3_0__dq__io(dram_dq),
    .ddr3_0__dqs__p(dram_dqs),
    .ddr3_0__clk__io(dram_ck),
    .ddr3_0__clk_en__io(dram_cke),
    .ddr3_0__we__io(dram_we_n),
    .ddr3_0__ras__io(dram_ras_n),
    .ddr3_0__cas__io(dram_cas_n),
    .ddr3_0__a__io(dram_a),
    .ddr3_0__ba__io(dram_ba),
    .ddr3_0__dm__io(dram_dm),
    .ddr3_0__odt__io(dram_odt),
    .wishbone_0__adr__io(wishbone_adr),
    .wishbone_0__dat_r__io(wishbone_dat_r),
    .wishbone_0__dat_w__io(wishbone_dat_w),
    .wishbone_0__cyc__io(wishbone_cyc),
    .wishbone_0__stb__io(wishbone_stb),
    .wishbone_0__sel__io(wishbone_sel),
    .wishbone_0__ack__io(wishbone_ack),
    .wishbone_0__we__io(wishbone_we),
    .clk100_0__io(clkin),
    .rst_0__io(1'b0)
  );

  initial
    begin
      $dumpfile("simsoc.fst");
      $dumpvars(0, clkin);
      $dumpvars(0, dram_dq);
      $dumpvars(0, dram_dqs);
      $dumpvars(0, dram_ck);
      $dumpvars(0, dram_cke);
      $dumpvars(0, dram_we_n);
      $dumpvars(0, dram_ras_n);
      $dumpvars(0, dram_cas_n);
      $dumpvars(0, dram_a);
      $dumpvars(0, dram_ba);
      $dumpvars(0, dram_dm);
      $dumpvars(0, dram_odt);
      $dumpvars(0, wishbone_adr);
      $dumpvars(0, wishbone_dat_w);
      $dumpvars(0, wishbone_dat_r);
      $dumpvars(0, wishbone_ack);
      $dumpvars(0, wishbone_stb);
      $dumpvars(0, wishbone_cyc);
      $dumpvars(0, wishbone_sel);
      $dumpvars(0, wishbone_we);
      $dumpvars(0, simsoctop);
      $dumpvars(0, ram_chip);
    end

  // UART
  reg [31:0] tmp;
  initial
    begin
      dram_rst = 1;
      #350; // Wait for RESET and POR

      // Software control
      dram_rst = 0;

      #10;

      $display("Release RESET_N");
      wishbone_write(32'h0000900c >> 2, 32'h0); // p0 address
      wishbone_write(32'h00009010 >> 2, 32'h0); // p0 baddress
      wishbone_write(32'h00009000 >> 2, 8'h0C); // DFII_CONTROL_ODT|DFII_CONTROL_RESET_N
      $display("Enable CKE");
      wishbone_write(32'h00009000 >> 2, 8'h0E); // DFII_CONTROL_ODT|DFII_CONTROL_RESET_N|DFI_CONTROL_CKE
      if (dram_cke != 1)
        begin
          $display("CKE activation failure");
          $finish;
        end

      // Set MR2
      $display("Set MR2");
      wishbone_write(32'h0000900c >> 2, 32'h200); // p0 address
      wishbone_write(32'h00009010 >> 2, 32'h2); // p0 baddress
      wishbone_write(32'h00009004 >> 2, 8'h0F); // RAS|CAS|WE|CS
      wishbone_write(32'h00009008 >> 2, 8'h01); // Command issue strobe

      // Set MR3
      $display("Set MR3");
      wishbone_write(32'h0000900c >> 2, 32'h0); // p0 address
      wishbone_write(32'h00009010 >> 2, 32'h3); // p0 baddress
      wishbone_write(32'h00009004 >> 2, 8'h0F); // RAS|CAS|WE|CS
      wishbone_write(32'h00009008 >> 2, 8'h01); // Command issue strobe

      // Set MR1
      $display("Set MR1");
      wishbone_write(32'h0000900c >> 2, 32'h6); // p0 address
      wishbone_write(32'h00009010 >> 2, 32'h1); // p0 baddress
      wishbone_write(32'h00009004 >> 2, 8'h0F); // RAS|CAS|WE|CS
      wishbone_write(32'h00009008 >> 2, 8'h01); // Command issue strobe

      // Set MR0
      $display("Set MR0");
      wishbone_write(32'h0000900c >> 2, 32'h320); // p0 address
      wishbone_write(32'h00009010 >> 2, 32'h0); // p0 baddress
      wishbone_write(32'h00009004 >> 2, 8'h0F); // RAS|CAS|WE|CS
      wishbone_write(32'h00009008 >> 2, 8'h01); // Command issue strobe
      wishbone_write(32'h0000900c >> 2, 32'h220); // p0 address
      wishbone_write(32'h00009010 >> 2, 32'h0); // p0 baddress
      wishbone_write(32'h00009004 >> 2, 8'h0F); // RAS|CAS|WE|CS
      wishbone_write(32'h00009008 >> 2, 8'h01); // Command issue strobe
      #6000; // tDLLK

      // ZQ calibration
      $display("Start ZQ calibration");
      wishbone_write(32'h0000900c >> 2, 32'h400); // p0 address (A10=1)
      wishbone_write(32'h00009010 >> 2, 32'h0); // p0 baddress
      wishbone_write(32'h00009004 >> 2, 8'h03); // WE|CS
      wishbone_write(32'h00009008 >> 2, 8'h01); // Command issue strobe
      #6000; // tZQinit

      // Hardware control
      wishbone_write(32'h00009000 >> 2, 8'h01); // DFII_CONTROL_SEL
      #2000;

      // Read test on provisioned data, row 0, col 0-7
      wishbone_read(32'h10000000 >> 2, tmp);
      assert_equal_32(tmp, 32'hFACECA8C);
      wishbone_read(32'h10000004 >> 2, tmp);
      assert_equal_32(tmp, 32'h0A0A0A0A);
      wishbone_read(32'h10000008 >> 2, tmp);
      assert_equal_32(tmp, 32'hFAAFFEEF);
      wishbone_read(32'h1000000C >> 2, tmp);
      assert_equal_32(tmp, 32'h12345678);

      // Read test on provisioned data, row 0, col 8-15
      wishbone_read(32'h10000010 >> 2, tmp);
      assert_equal_32(tmp, 32'h33333333);
      wishbone_read(32'h10000014 >> 2, tmp);
      assert_equal_32(tmp, 32'h22222222);
      wishbone_read(32'h10000018 >> 2, tmp);
      assert_equal_32(tmp, 32'h11111111);
      wishbone_read(32'h1000001C >> 2, tmp);
      assert_equal_32(tmp, 32'h00000000);

      // Read test on provisioned data, row 0, col 16-23
      wishbone_read(32'h10000020 >> 2, tmp);
      assert_equal_32(tmp, 32'hA0A0A0A0);
      wishbone_read(32'h10000024 >> 2, tmp);
      assert_equal_32(tmp, 32'h55556666);
      wishbone_read(32'h10000028 >> 2, tmp);
      assert_equal_32(tmp, 32'h01020304);
      wishbone_read(32'h1000002C >> 2, tmp);
      assert_equal_32(tmp, 32'hF00DF00D);

      // Read test on provisioned data, row 0, col 24-31
      wishbone_read(32'h10000030 >> 2, tmp);
      assert_equal_32(tmp, 32'hAAAAAAAA);
      wishbone_read(32'h10000034 >> 2, tmp);
      assert_equal_32(tmp, 32'h000C0C0A);
      wishbone_read(32'h10000038 >> 2, tmp);
      assert_equal_32(tmp, 32'h000CACA0);
      wishbone_read(32'h1000003C >> 2, tmp);
      assert_equal_32(tmp, 32'hC0CAC0CA);

      // Write
      wishbone_write(32'h1000000C >> 2, 32'h00BA0BAB);
      wishbone_write(32'h10000008 >> 2, 32'h13374242);
      wishbone_write(32'h10000004 >> 2, 32'hC0DEC0DE);
      wishbone_write(32'h10000000 >> 2, 32'h01020304);

      wishbone_read(32'h10000000 >> 2, tmp);
      assert_equal_32(tmp, 32'h01020304);
      wishbone_read(32'h10000004 >> 2, tmp);
      assert_equal_32(tmp, 32'hC0DEC0DE);
      wishbone_read(32'h10000008 >> 2, tmp);
      assert_equal_32(tmp, 32'h13374242);
      wishbone_read(32'h1000000C >> 2, tmp);
      assert_equal_32(tmp, 32'h00BA0BAB);

      $finish;
    end

  task wishbone_write;
    input [31:0] address;
    input [31:0] value;

    begin
      wishbone_adr = address;
      wishbone_dat_w = value;
      wishbone_cyc = 1;
      wishbone_stb = 1;
      wishbone_sel = 4'hF;
      wishbone_we = 1;

      while (wishbone_ack == 0)
        begin
          #10;
        end

      wishbone_cyc = 0;
      wishbone_stb = 0;

      #10;
    end
  endtask

  task wishbone_read;
    input [31:0] address;
    output [31:0] value;

    begin
      wishbone_adr = address;
      wishbone_we = 0;
      wishbone_cyc = 1;
      wishbone_stb = 1;
      wishbone_sel = 4'hF;

      while (wishbone_ack == 0)
        begin
          #10;
        end

      value = wishbone_dat_r;
      wishbone_cyc = 0;
      wishbone_stb = 0;

      #10;
    end
  endtask

  task assert_equal_32;
    input [31:0] inA;
    input [31:0] inB;

    begin
      if (inA != inB)
        begin
          $display("%m at %t: Assertion failed (32-bit) equality: %08x != %08x", $time, inA, inB);
          $finish;
        end
    end
  endtask

  integer i;
  integer tstart;
  integer tend;

  task speedtest_read;
    begin
      tstart = $time;
      for (i = 0; i < 10; i = i+1) begin
        wishbone_read(32'h10000000 >> 2, tmp);
        wishbone_read(32'h10000004 >> 2, tmp);
        wishbone_read(32'h10000008 >> 2, tmp);
        wishbone_read(32'h1000000C >> 2, tmp);
        wishbone_read(32'h10000010 >> 2, tmp);
        wishbone_read(32'h10000014 >> 2, tmp);
        wishbone_read(32'h10000018 >> 2, tmp);
        wishbone_read(32'h1000001C >> 2, tmp);
        wishbone_read(32'h10000020 >> 2, tmp);
        wishbone_read(32'h10000024 >> 2, tmp);
        wishbone_read(32'h10000028 >> 2, tmp);
        wishbone_read(32'h1000002C >> 2, tmp);
        wishbone_read(32'h10000030 >> 2, tmp);
        wishbone_read(32'h10000034 >> 2, tmp);
        wishbone_read(32'h10000038 >> 2, tmp);
        wishbone_read(32'h1000003C >> 2, tmp);
      end
      tend = $time;

      //$display("Read speedtest: %d B/s", (10*16*4)*1000000000/(1024*1024)/(tend-tstart));
      $display("Read speedtest: %d MB/s", 610352/(tend-tstart));
    end
  endtask

    task speedtest_write;
    begin
      tstart = $time;
      for (i = 0; i < 10; i = i+1) begin
        wishbone_write(32'h1000000C >> 2, 32'h00BA0BAB);
        wishbone_write(32'h10000008 >> 2, 32'h13374242);
        wishbone_write(32'h10000004 >> 2, 32'hC0DEC0DE);
        wishbone_write(32'h10000000 >> 2, 32'h01020304);
        wishbone_write(32'h1000001C >> 2, 32'h00BA0BAB);
        wishbone_write(32'h10000018 >> 2, 32'h13374242);
        wishbone_write(32'h10000014 >> 2, 32'hC0DEC0DE);
        wishbone_write(32'h10000010 >> 2, 32'h01020304);
        wishbone_write(32'h1000002C >> 2, 32'h00BA0BAB);
        wishbone_write(32'h10000028 >> 2, 32'h13374242);
        wishbone_write(32'h10000024 >> 2, 32'hC0DEC0DE);
        wishbone_write(32'h10000020 >> 2, 32'h01020304);
        wishbone_write(32'h1000003C >> 2, 32'h00BA0BAB);
        wishbone_write(32'h10000038 >> 2, 32'h13374242);
        wishbone_write(32'h10000034 >> 2, 32'hC0DEC0DE);
        wishbone_write(32'h10000030 >> 2, 32'h01020304);
      end
      tend = $time;

      //$display("Write speedtest: %d B/s", (10*16*4)*1000000000/(1024*1024)/(tend-tstart));
      $display("Write speedtest: %d MB/s", 610352/(tend-tstart));
    end
  endtask
endmodule
